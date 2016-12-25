#!/usr/bin/env python
#
# Read from 
import logging
import logging.config
import os
import getopt
import sys
import urllib2
import json
import random
import time
import struct
import socket
import jphconfig
import select
import math

adc=""

def initJPH(type):
    global adc
    if type == "ADCpiReader":
        try:
            sys.path.append("/home/jphmonitor")
            sys.path.append('/home/jphmonitor/ABElectronics_Python_Libraries/ADCPi')
            from ABE_ADCPi import ADCPi
            from ABE_helpers import ABEHelpers
            i2c_helper = ABEHelpers()
            bus = i2c_helper.get_smbus()
            adc = ADCPi(bus, 0x68, 0x69, 12)
        except ImportError:
            print ("in sensors, importing ABE_ADCPi failed")
            sys.exit()
    if type == "ADAfruitReader":
        import Adafruit_DHT
    # if type == "failsafeReader":
    #     import requests

# -------------
# Read Startup Parameters
# -------------
def readParams(configURL, Codifier):

    def usage():
        print("Usage: -u <url>", __file__)
        print("\t-u <url> : load the JSON configuration from a url")
        print("\t-c <code>: The Sensor that this program needs to manage") 

    configURL=os.getenv("JPH_CONFIG", configURL)
    Codifier=os.getenv("JPH_SENSOR", "")

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hu:c:", ["help", "url=", "code="])
        for opt, arg in opts:
            if opt in ("-h", "help"):
                raise
            elif opt in ("-u", "--url"):
                configURL=arg
            elif opt in ("-c", "--code"):
                Codifier=arg
        if Codifier == "" :
            raise ValueError("Option <code> is mandatory")
        if configURL == "" :
            raise ValueError("Option <url> is mandatory")
    except Exception as e:
        print("Error: %s" % e)
        usage()
        sys.exit()
    return (configURL, Codifier)

def main(isActive):

    ctrlSocket=jphconfig.openControlChannel(
        configJSON["Multicast"]["Control-Channel"]["Address"],
        configJSON["Multicast"]["Control-Channel"]["Port"])
    ctrlNextKeepAlive=0
    jphconfig.prepareDataChannel(
        configJSON["Multicast"]["Data-Channel"]["Address"],
        configJSON["Multicast"]["Data-Channel"]["Port"])
    makeNextSensorReading=0

    inputs = [ctrlSocket]
    forever=True
    while forever:
        t=int(time.time()) 

        # send a keepalive packet
        if t >= ctrlNextKeepAlive:
            seq=jphconfig.sendPing(t, Codifier, isActive)
            logging.debug("Ctrl-I : send %s %s %s %s", Codifier, t, seq, isActive)
            if not isActive:
                logger.info("Keep Alive send. Processing currently HALTED.")
            ctrlNextKeepAlive = t + mySensor["KeepAliveInterval"]

        if t >= makeNextSensorReading:
            if isActive:
                eval(mySensor["Sensor"]["Type"]+'(t)')
                makeNextSensorReading = t + mySensor["SensorInterval"]

        # last parameter in select is timeout in seconds
        timeout=(max(0.001, (min(makeNextSensorReading, ctrlNextKeepAlive) - t)))
        readable, writable, exceptional = select.select(inputs, [], [], timeout)
        for s in readable:
            if s == ctrlSocket:
                data, sender = ctrlSocket.recvfrom(1500)
            (timestamp, source, flag, length,), value = struct.unpack('I2s1sI', data[:12]), data[12:]
            
            # Process Ctrl Messages
            if source in (Codifier, "@@"):
                if flag == 'C':
                    logger.info("Ctrl-C - recv %s %s Received request to reload config", source, timestamp)
                    forever=False
                    break
                if flag == 'H':
                    logging.info("Ctrl-H - recv %s %s Received request to halt sensor", source, timestamp)
                    isActive=False
                    ctrlNextKeepAlive=0     # force to send out a status change ping
                if flag == 'S':
                    logging.info("Ctrl-I - recv %s %s Received request to start sensor", source, timestamp)
                    isActive=True
                    ctrlNextKeepAlive=0     # force to send out a status change ping
                if flag == 'I':
                    seq2, isActive2 = struct.unpack('I?', value)
                    logging.debug("Ctrl-I : recv %s %s %s %s", source, timestamp, seq2, isActive2)
                    if seq2 != seq and source == myCodifier:
                        logging.critical("There is another instance of %s running (seq=%s)", Codifier, str(seq2))
                        sys.exit()

def sendSensor(sendTime, sendCodifier, sendValue):
    if type(sendValue) == type(int()):
        payload_type = 'i'
        packed = struct.pack(payload_type, sendValue)
    elif isinstance(sendValue, str):
        payload_type = 's'
        packed = struct.pack('I%ds' % (len(sendValue),), len(sendValue), sendValue)
    elif isinstance(sendValue, float):
        payload_type = 'f'
        packed = struct.pack(payload_type, sendValue)
    else:
        logger.critical('notyetcoded: %s', payload)
        sys.exit()
    logger.debug("Data-%s : send %s %d %s", payload_type, sendCodifier, sendTime, sendValue)
    jphconfig.sendDataChannel(sendTime, sendCodifier, payload_type, packed)
       
def phobya2temp(voltageOut):
    ohm=(5-voltageOut)/voltageOut*16800/1000
    temp=(0.0755*math.pow(ohm,2))-4.2327*ohm+60.589
    return temp

def ADCpiReader(Timestamp):
    try:
        v = adc.read_voltage(int(mySensor["Sensor"]["Pin"]))
        sendSensor(Timestamp, Codifier, phobya2temp(v))
        for proxy in mySensor["Sensor"]["Proxy"]:
            v = adc.read_voltage(int(proxy["Pin"]))
            sendSensor(Timestamp, str(proxy["Codifier"]), v)
    except KeyError as e:
        logger.critical("Exception (Field not found?): %s", e)
    except Exception as e:
        logger.critical("Exception : %s", e)

def ADAfruitReader(Timestamp):
    try:
        import Adafruit_DHT
        h, v = Adafruit_DHT.read_retry(Adafruit_DHT.AM2302, int(mySensor["Sensor"]["Pin"]))
        if h is None and v is None:
            raise("sensors return None")
        sendSensor(Timestamp, Codifier, v)
        for proxy in mySensor["Sensor"]["Proxy"]:
            sendSensor(Timestamp, str(proxy["Codifier"]), h)

    except KeyError as e:
        logger.critical("Exception (Field not found?): %s", e)
    except Exception as e:
        logger.critical("Exception : %s", e)


def TempLinux(Timestamp):
    try:
        f = os.popen("/bin/cat " + mySensor["Sensor"]["Pipe"])
        sendSensor(Timestamp, Codifier, float(f.read())/1000)
    except KeyError as e:
        logger.critical("Exception (Field not found?): %s", e)
    except Exception as e:
        logger.critical("Exception : %s", e)
       
def failsafeReader(Timestamp):
    try:
        import requests
        response=requests.get(mySensor["Sensor"]["URL"], timeout=(2.0, 10.0))
        if response.headers["content-type"] != "application/json":
            raise WrongContent(response=response)
        else:
            json_data = json.loads(response.text)
            v=json_data[mySensor["Sensor"]["Field"]]
            sendSensor(Timestamp, Codifier, v)
            for proxy in mySensor["Sensor"]["Proxy"]:
                v=json_data[proxy["Field"]]
                sendSensor(Timestamp, str(proxy["Codifier"]), v)
    except KeyError as e:
        logger.critical("Exception (Field not found?): %s", e)
    except requests.exceptions.ConnectionError as e:
        logger.warning("Unexpected not found: %s", e)
    except requests.exceptions.ReadTimeout as e:
        logger.critical("Slow HTTP: %s", e)
    except ValueError as e:
        logger.critical("Failed to read HTTP: %s", e)
    except Exception as e:
        logger.critical("Exception : %s", e)

if __name__ == '__main__':

    # - return location of the config file and my Codifier (from params or ENVIRONMENT)
    (configURL, Codifier)=readParams("file:static/jphmonitor.json", "")
    isActive=""     # At startup base Active-flag on config after that from CTRL-CHNL

    while True:
        (logger, configJSON, mySensor, isActive)=jphconfig.loadconfig(configURL, Codifier, isActive)
        initJPH(mySensor["Sensor"]["Type"])

        if mySensor["Sensor"]["Type"] == "":
            logger.critical("Exepecting a Sensor:Type for %s", Codifier)
            sys.exit()

        main(isActive)
