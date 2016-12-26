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
import select
import jphconfig

# -------------
# Read Startup Parameters
# -------------
def readParams(configURL, Codifier):
    def usage():
        print("Usage: -u <url> -c <code> -t <code> -f <flag> -l <code> -x", __file__)
        print("\t-u <url> : load the configuration from a url")
        print("\t-c <code>: The Codifier of this program") 
        print("\t-t <code>: The Codifier of the program to send a message to") 
        print("\t-f <flag>: Send a signal (H)alt, (S)tart, (C)onfig")
        print("\t-l <code>: Filter ond show only this Codifier") 
        print("\t-x       : Exit (skip view messages on console")

    configURL=os.getenv("JPH_CONFIG", configURL)
    comTarget=""
    comflag=""
    comFilter=""
    comflagExit=False

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hu:c:t:f:l:x", ["help", "url=", "code=", "comTarget=", "flag=", "filter=", "exit"])
        for opt, arg in opts:
            if opt in ("-h", "help"):
                usage()
                sys.exit()
            elif opt in ("-u", "--url"):
                configURL=arg
            elif opt in ("-c", "--code"):
                Codifier=arg
            elif opt in ("-t", "--filter"):
                comTarget=arg
            elif opt in ("-f", "--flag"):
                comflag=arg
            elif opt in ("-l", "--filter"):
                comFilter=arg
            elif opt in ("-x", "--exit"):
                comflagExit=True
        if Codifier == "" :
            raise ValueError("Option <code> is mandatory")
        if configURL == "" :
            raise ValueError("Option <url> is mandatory")
        if (comTarget!="" and comflag=="") or (comTarget=="" and comflag!=""):
            raise ValueError("Option -t & -f are combined")
    except Exception as e:
        print("Error: %s" % e)
        usage()
        sys.exit()
    return (configURL, Codifier, comTarget, comFilter, comflag, comflagExit)

def main(isActive):

    # Count the number of Multicast packets
    Counter=0

    ctrlSocket=jphconfig.openControlChannel(
        str(configJSON["Multicast"]["Control-Channel"]["Address"]),
        int(configJSON["Multicast"]["Control-Channel"]["Port"]))
    ctrlNextKeepAlive=0
    dataSocket=jphconfig.openDataChannel(
        str(configJSON["Multicast"]["Data-Channel"]["Address"]),
        int(configJSON["Multicast"]["Data-Channel"]["Port"]))
    makeNextSensorReading = int(time.time()) + mySensor["SensorInterval"]
 
    if comTarget != "":
        leftc=comflag[:1]
        t=int(time.time()) 
        seq_packed = struct.pack('I', t)
        print("Sending flag=%s to Codifier=%s" % (leftc, comTarget))
        jphconfig.sendControlChannel(t, comTarget, leftc, seq_packed)

    if comflagExit:
        sys.exit()

    # Use select to listen to both channels
    inputs = [dataSocket, ctrlSocket]
    forever=True
    while forever:
        t=int(time.time()) 
        
        # send a keepalive packet
        if t >= ctrlNextKeepAlive:
            jphconfig.sendPing(t, Codifier, False)
            logging.debug("Ctrl-I : send %s %s %s", t, jphconfig.getReloadTime(), False)
            ctrlNextKeepAlive = t + mySensor["KeepAliveInterval"]

        if t >= makeNextSensorReading:
            payload_type = 'i'
            packed = struct.pack(payload_type, Counter)
            if isActive:
                jphconfig.sendDataChannel(t, Codifier, payload_type, packed)
            Counter=0
            makeNextSensorReading = t + mySensor["SensorInterval"]


        # last parameter in select is timeout in seconds
        timeout=(max(0.001, (ctrlNextKeepAlive - t)))
        readable, writable, exceptional = select.select(inputs, [], [], timeout)
        for s in readable:
            if s == dataSocket:
                data, sender = dataSocket.recvfrom(1500)
            if s == ctrlSocket:
                data, sender = ctrlSocket.recvfrom(1500)
            (timestamp, source, flag, length,), value = struct.unpack('I2s1sI', data[:12]), data[12:]
            Counter+=1
            
            # Process Messages
            if flag in ('H', 'S', 'C', 'I', 'T', 'P'):
                chnl="Ctrl-"
                if flag in ('T', 'P'):
                    payload, = struct.unpack('I', value)
                elif flag == 'I':
                    seq2, isActive2 = struct.unpack('I?', value)
                    payload=("%s / %s" % (seq2, isActive2))
                else:
                    payload = None
            else:
                chnl="Data-"
                if flag == 'f':
                    payload, = struct.unpack('f', value)
                elif flag == 'i':
                    payload, = struct.unpack('I', value)
                elif flag == 's':
                    (i,), string = struct.unpack("I", value[:4]), value[4:]
                    payload = string
                else:
                    payload=value
                    logger.critical("Message type (%s) not yet supported", flag)

            if comFilter in (source, ""):
                print("%d %s%s %s %s (len=%d)" % (timestamp, chnl, flag, source,
                       payload, length)), sender

            if source in (Codifier, "@@"):
                if flag == 'I':
                    seq2, isActive2 = struct.unpack('I?', value)
                    logging.debug("Ctrl-I : recv %s %s %s", timestamp, seq2, isActive2)
                    if seq2 >= jphconfig.getReloadTime() and source == Codifier:
                        logging.warn("There is another instance of %s running (seq=%s) - ignore", Codifier, str(seq2))
                if flag == 'C':
                    logger.info("Ctrl-C - Received request to reload config")
                    forever=False
                    break

    # exit
    jphconfig.closeControlChannel()
    jphconfig.closeDataChannel()

if __name__ == '__main__':

    # - return location of the config file and my Codifier (from params or ENVIRONMENT)
    (configURL, Codifier, comTarget, comFilter, comflag, comflagExit)=readParams("file:static/jphmonitor.json", "CC")
    isActive=""     # At startup base Active-flag on config after that from CTRL-CHNNL
    while True:
        (logger, configJSON, mySensor, isActive)=jphconfig.loadconfig(configURL, Codifier, isActive)

        if isActive:
            logger.warn("Configuration is setup to Active=True (This should be changed)")
        else:
            isActive=True
        if mySensor["Sensor"]["Type"] != "ControlProgram":
            logger.critical("Sensor type (ControlProgram) expected for %s", Codifier)
            sys.exit()

        main(isActive)
        comTarget=""                # Reset the command for the second time around
