#!/usr/bin/env python
#
# Should redis not be able to reload its config - listning to control messages?
#
# Read from 
import logging
import logging.config
import os
import getopt
import sys
import urllib2
import json
import struct
import socket
import select
import psycopg2
import jphconfig
import time
import random

# -----------------------
# Read startup parameters
# -----------------------
def readParams(configURL, Codifier):

    def usage():
        print("Usage: -u <url>", __file__)
        print("\t-u <url> : load the JSON configuration from a url")
        print("\t-c <code>: The Sensor that this program needs to manage") 

    configURL=os.getenv("JPH_CONFIG", configURL)

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

    try:
        f = open(os.path.expanduser(mySensor["Sensor"]["SQL"]["Password"]))
        sqlpassword=f.read().strip()
        f.close
    except:
        logger.critical("Unexpected error reading %s", mySensor["Sensor"]["SQL"]["Password"])
        sys.exit()

    # connecto to Postgresql
    try:
        qs=("dbname=%s user=%s password=%s host=%s " % (mySensor["Sensor"]["SQL"]["Database"],
            mySensor["Sensor"]["SQL"]["User"], sqlpassword, mySensor["Sensor"]["SQL"]["Host"]))
        q=psycopg2.connect(qs)
    except psycopg2.OperationalError as e:
        logging.critical("Unable to connect: %s", format(e))
        sys.exit()
    except Exception as e:
        logging.critical("Unexepected error: %s", e)
        sys.exit()
    Counter=0

    ctrlSocket=jphconfig.openControlChannel(
        configJSON["Multicast"]["Control-Channel"]["Address"],
        configJSON["Multicast"]["Control-Channel"]["Port"])
    ctrlNextKeepAlive=0
    dataSocket=jphconfig.openDataChannel(
        configJSON["Multicast"]["Data-Channel"]["Address"],
        configJSON["Multicast"]["Data-Channel"]["Port"])
    makeNextSensorReading = int(time.time()) + mySensor["SensorInterval"]

    # Use select to listen to both channels
    inputs = [dataSocket, ctrlSocket]
    forever=True
    while forever:
        t=int(time.time()) 
        
        # send a keepalive packet
        if t >= ctrlNextKeepAlive:
            jphconfig.sendPing(t, Codifier, isActive)
            logging.debug("Ctrl-I : send %s %s %s", t, jphconfig.getReloadTime(), isActive)
            if not isActive:
                logger.info("Keep Alive send. Processing currently HALTED.")
            ctrlNextKeepAlive = t + mySensor["KeepAliveInterval"]

        if t >= makeNextSensorReading:
            payload_type = 'i'
            packed = struct.pack(payload_type, Counter)
            if isActive:
                jphconfig.sendDataChannel(t, Codifier, payload_type, packed)
            Counter=0
            makeNextSensorReading = t + mySensor["SensorInterval"]

        # last parameter in select is timeout in seconds
        timeout=(max(0.001, (min(makeNextSensorReading, ctrlNextKeepAlive) - t)))
        readable, writable, exceptional = select.select(inputs, [], [], timeout)
        for s in readable:
            if s == dataSocket:
                data, sender = dataSocket.recvfrom(1500)
            if s == ctrlSocket:
                data, sender = ctrlSocket.recvfrom(1500)
            (timestamp, source, flag, length,), value = struct.unpack('I2s1sI', data[:12]), data[12:]
            
            # Process Ctrl Messages
            if source in (Codifier, "@@"):
                if flag == 'C':
                    logger.info("Ctrl-C - Received request to reload config")
                    forever=False
                    break
                if flag == 'T':
                    RequestTime, = struct.unpack('I', value)
                    logger.debug("Ctrl-T - Received time info %s (ignore)", RequestTime)
                if flag == 'P':
                    RequestTime, = struct.unpack('I', value)
                    logging.debug("Ctrl-P - Received request for time %s", RequestTime)
                    jphconfig.sendTime(t, Codifier, RequestTime)
                if flag == 'H':
                    logging.info("Ctrl-H - Received request to halt sensor")
                    isActive=False
                    ctrlNextKeepAlive=0     # force to send out a status change ping
                if flag == 'S':
                    logging.info("Ctrl-I - Received request to start sensor")
                    isActive=True
                    ctrlNextKeepAlive=0     # force to send out a status change ping
                if flag == 'I':
                    seq2, isActive2 = struct.unpack('I?', value)
                    logging.debug("Ctrl-I : recv %s %s %s", timestamp, seq2, isActive2)
                    if seq2 >= jphconfig.getReloadTime() and source == Codifier:
                        logging.critical("There is another instance of %s running (seq=%s)", Codifier, str(seq2))
                        sys.exit()

            # message types in lowercase is always data channel
            if isActive:
                if flag in ('i', 'f', 's'):
                    if flag in ('f'):
                        payload, = struct.unpack('f', value)
                    elif flag in ('i'):
                        payload, = struct.unpack('I', value)
                    elif flag == 's':
                        (i,), string = struct.unpack("I", value[:4]), value[4:]
                        payload = string
                    else:
                        payload=value
                        logger.critical("Message type (%s) not yet supported: %s", flag, payload)
                        sys.exit()

                    try:
                        cursor = q.cursor()
                        ans=("INSERT INTO sensor_{} VALUES (to_timestamp({}), {})".format(source, timestamp, payload))
                        logger.debug(ans)
                        cursor.execute(ans)
                        q.commit()
                        Counter+=1
                    except Exception as e:
                        logger.critical("Unexpected SQL error: %s", e)
                        forever=False

    # exit
    ctrlSocket.close()
    dataSocket.close()
    q.close
            
if __name__ == '__main__':

    # - return location of the config file and my Codifier (from params or ENVIRONMENT)
    (configURL, Codifier)=readParams("file:static/jphmonitor.json", "Q1")
    isActive=""     # At startup base Active-flag on config after that from CTRL-CHNNL
    while True:
        (logger, configJSON, mySensor, isActive)=jphconfig.loadconfig(configURL, Codifier, isActive)

        if mySensor["Sensor"]["Type"] != "SQLLoader":
            logger.critical("Sensor type (SQLLoader) expected for %s", Codifier)
            sys.exit()

        main(isActive)
