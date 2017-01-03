#!/usr/bin/env python
from __future__ import print_function, absolute_import, division, nested_scopes, generators, unicode_literals
import sys
import getopt
import struct
import jph
import os
import time
import random
import math

# -------------
# Globals
# -------------
configURL="file:static/config.json"
Codifier=""

# -------------
# Read Startup Parameters
# -------------
def usage():
    print("Usage: -u <url>", __file__)
    print("\t-u <url> : load the JSON configuration from a url")
    print("\t-c <code>: The Sensor that this program needs to manage") 

try:
    opts, args = getopt.getopt(sys.argv[1:], "hu:c:", ["help", "url=", "code="])
    for opt, arg in opts:
        if opt in ("-h", "help"):
            raise
        elif opt in ("-u", "--url"):
            configURL=arg
        elif opt in ("-c", "--code"):
            Codifier=arg
except Exception as e:
    print("Error: %s" % e)
    usage()
    sys.exit()

#
# by making a Sensor a class you can store local variables
# and make a function to check the sensor every x seconds but only update the 
# data if the sensor changed within a specific tollerance
# 
# Also allow for enhanced inequiry capabilities using a peer-to-peer future prototcol
#
def theOutput(chnl, flag, source, to, timestamp, sequence, length, sender, data, isActive):

    comA = True if comAll in (source, to, "") else False
    if (comFrom!=""):
        comA = True if comFrom == source else False
    if (comTo!=""):
        comA = True if comTo == to else False

    comC = True if comChnl in (chnl[:1], "") else False

    if comA and comC:
        print("%d %s%s %s-%s %d (len=%d) (active=%s) %s" % (timestamp, chnl, flag, source, to, sequence, length, isActive, data ), sender)

class TempLinux(object):
    def read(self, Timestamp):
        try:
            channel.sendData(float(os.popen(self.cmd).read())/1000)
        except AttributeError:
            self.cmd= ("/bin/cat " + channel.getMySensorElement("Pipe"))
            channel.sendData(float(os.popen(self.cmd).read())/1000)
        # channel.sendData(random.randint(1,2147483647), Codifier="XX")

class failsafeReader(object):
    def read(self, Timestamp):
        # try:
        s=channel.getMySensorElement("URL")
        response=requests.get(s, timeout=(2.0, 10.0))
        if response.headers["content-type"] != "application/json":
            raise WrongContent(response=response)
        else:
            if (len(response.text) > 1):
                json_data = json.loads(response.text.replace(",]}","]}"))
                v=json_data[channel.getMySensorElement("Field")]
                channel.sendData(data=v, Codifier="")
                for proxy in channel.getMySensorElement("Proxy"):
                     v=json_data[proxy["Field"]]
                     code=str(proxy["Codifier"])
                     channel.sendData(data=v, Codifier=str(proxy["Codifier"]))
        # Spend some time catchign error codes
        #  --- decide what should crash and when to continue
        # except KeyError as e:
        #     channel.logger.critical("Exception (Field not found?): %s", e)
        # except requests.exceptions.ConnectionError as e:
        #     channel.logger.warning("Unexpected not found: %s", e)
        # except requests.exceptions.ReadTimeout as e:
        #     logger.critical("Slow HTTP: %s", e)
        # except ValueError as e:
        #     logger.critical("Failed to read HTTP: %s", e)
        # except Exception as e:
        #     channel.logger.critical("Exception : %s", e)

class ADCpiReader(object):
    def phobya2temp(self, voltageOut):
        ohm=(5-voltageOut)/voltageOut*16800/1000
        temp=(0.0755*math.pow(ohm,2))-4.2327*ohm+60.589
        return temp

    def read(self, Timestamp):
        v = adc.read_voltage(int(channel.getMySensorElement("Pin")))
        channel.sendData(data=self.phobya2temp(v))
        for proxy in channel.getMySensorElement("Proxy"):
            v = adc.read_voltage(int(proxy["Pin"]))
            channel.sendData(data=self.phobya2temp(v), Codifier=str(proxy["Codifier"]))

class ADAfruitReader(object):
    def read(self, Timestamp):
        h, v = Adafruit_DHT.read_retry(Adafruit_DHT.AM2302, int(channel.getMySensorElement("Pin")))
        if h is None and v is None:
            print("SENSORS RETURN NO VALUES BRO")
        else:
            channel.sendData(data=v)
            for proxy in channel.getMySensorElement("Proxy"):
                 channel.sendData(data=h, Codifier=str(proxy["Codifier"]))

if __name__ == '__main__':

    channel=jph.jph(configURL=configURL, Codifier=Codifier)

    type=channel.getMySensor()["Type"]
    if type == "ADAfruitReader":
        import Adafruit_DHT
    if type == "failsafeReader":
        import requests
        import json
    if type == "ADCpiReader":
        sys.path.append("/home/jphmonitor")
        sys.path.append('/home/jphmonitor/ABElectronics_Python_Libraries/ADCPi')
        from ABE_ADCPi import ADCPi
        from ABE_helpers import ABEHelpers
        i2c_helper = ABEHelpers()
        bus = i2c_helper.get_smbus()
        adc = ADCPi(bus, 0x68, 0x69, 12)

    c=eval(type + '()')
    channel.run(timeCallback=c.read )

