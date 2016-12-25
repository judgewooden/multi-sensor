# ------------------------------------------
# Load the config for JPH & setup a logger
# ------------------------------------------
import os
import logging
import logging.config
import sys
import json
import urllib2
import struct
import socket
import random
import __main__ as main

#
# Global for tbhis sub
#
dataAddress=""
dataPort=""
dataSocket=""
ctrlAddress=""
ctrlPort=""
ctrlSocket=""

def loadconfig(configURL="", myCodifier="", isActive=""):

    if (os.getenv("JPH_DEBUG", "0")=="1"):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARN)
    logger=logging.getLogger()

    try:
        configJSON=json.loads(urllib2.urlopen(configURL).read())
    except Exception as e:
        logger.critical("Failed to parse json in %s (Error:%s)", configURL, e)
        sys.exit()

    try:
        mySensor=""
        for sensor in configJSON["Sensors"]:
            if sensor["Codifier"] == myCodifier:
                mySensor=sensor
                break

        if mySensor == "":
            logging.critical("Failed to find Sensor %s in configuration %s", myCodifier, configURL)
            sys.exit()            

        if isActive == "":    # only read the config at startup 
        	isActive = mySensor["Active"]

        tst = configJSON["Logging"]["root"]
        tst = configJSON["Logging"]["loggers"]["default"]
        tst = configJSON["Multicast"]["Control-Channel"]["Address"]
        tst = configJSON["Multicast"]["Control-Channel"]["Port"]
        tst = configJSON["Multicast"]["Data-Channel"]["Address"]
        tst = configJSON["Multicast"]["Data-Channel"]["Port"]
    except Exception as e:
        logging.critical("Failed to load mandatory field %s", e)
        sys.exit()

    #setup specific logger based on config file
    if (os.getenv("JPH_DEBUG", "0")!="1"):
        logging.config.dictConfig(configJSON["Logging"])
        foundLogger=""
        for logentry in configJSON["Logging"]["loggers"]:
            if logentry == main.__file__.split(".")[0] + '-' + myCodifier:
                foundLogger=logentry
        if foundLogger=="":
            for logentry in configJSON["Logging"]["loggers"]:
                if logentry == main.__file__.split(".")[0]:
                    foundLogger=logentry
        if foundLogger=="":
            for logentry in configJSON["Logging"]["loggers"]:
                if logentry == "default":
                    foundLogger=logentry
        if foundLogger=="":
            logger.warn("(Re)Starting. No logger found")
        else:
            logger=logging.getLogger(foundLogger)
            logger.info("(Re)Starting %s on logger: %s", main.__file__.split(".")[0] + '-' + myCodifier, foundLogger)
    else:
        logger.info("(Re)Starting logging in DEBUG")

    return (logger, configJSON, mySensor, isActive)

def openSocket(addr, port):
    tAddr = socket.getaddrinfo(addr, None)[0]
    tsocket = socket.socket(tAddr[0], socket.SOCK_DGRAM)
    tsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tsocket.bind(('', port))
    group_bin = socket.inet_pton(tAddr[0], tAddr[4][0])
    mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
    tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    return tsocket

def openControlChannel(address, port):
	global ctrlAddress, ctrlPort, ctrlSocket
	ctrlSocket=openSocket(address, port)
	ctrlAddress=address
	ctrlPort=port
	return ctrlSocket

def closeControlChannel():
	global ctrlAddress, ctrlPort, ctrlSocket
	ctrlSocket.close()
	ctrlAddress=""
	ctrlPort="" 
	ctrlSocket=""

def sendPing(Timestamp, Codifier, isActive):
    seq = random.randint(1,2147483647)
    packed = struct.pack('I?', seq, isActive)
    packed_data = struct.pack("I2s1sI%ds" % (len(packed),), Timestamp, Codifier, 'I', len(packed), packed)
    ctrlSocket.sendto(packed_data, (ctrlAddress, ctrlPort))
    return seq

def sendControlChannel(Timestamp, Codifier, MessageFlag, MessageData):
	print(Timestamp, Codifier, MessageFlag, MessageData)
	packed_data = struct.pack("I2s1sI%ds" % (len(MessageData),), Timestamp, Codifier, MessageFlag, len(MessageData), MessageData)
	ctrlSocket.sendto(packed_data, (ctrlAddress, ctrlPort))

def openDataChannel(address, port):
	global dataAddress, dataPort, dataSocket
	dataSocket=openSocket(address, port)
	dataAddress=address
	dataPort=port
	return dataSocket

def prepareDataChannel(address, port):
	global dataAddress, dataPort
	dataAddress=address
	dataPort=port

def closeDataChannel():
	global dataAddress, dataPort, dataSocket
	dataSocket.close()
	dataAddress=""
	dataPort=""
	dataSocket=""

def sendDataChannel(Timestamp, Codifier, MessageFlag, MessageData):
	packed_data = struct.pack("I2s1sI%ds" % (len(MessageData),), Timestamp, Codifier, MessageFlag, len(MessageData), MessageData)
	ctrlSocket.sendto(packed_data, (dataAddress, dataPort))
