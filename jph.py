from __future__ import print_function, absolute_import, division, nested_scopes, generators, unicode_literals
import os
import json
import urllib2
import logging.config
import socket
import struct
import random
# import time
import datetime 
import select
import sys

"""
Data Packet Types and payload

N   - Initialize 
    Q   Time when the Configuration was reset/loaded
    ?   indicate if senders data cannel is active (ignore)
I   - Keep Alive
    Q   Time when the confirmation was last loaded
    ?   indicate if senders data cannel is active (ignore)
P   - Ping Request 
    Q   The time that would be required in the response message (for syncing)
    ?   indicate if senders data cannel is active (ignore)
T   - Ping Response (TIME)
    Q   The time that was in the PING message
    ?   indicate if senders data cannel is active (ignore)
S   - Start a sensor DATA channel
    Q   Required but ignore
    ?   indicate if senders data cannel is active (ignore)
H   - Pause a sensor DATA channel
    Q   Time value Required but ignore
    ?   indicate if senders data cannel is active (ignore)
C   - Message to request a JSON reload and CTRL+DATA Channel Restart
    Q   Time value Required but ignore
    ?   indicate if senders data cannel is active (ignore)

Ctrl & Data Sequence numbers are reset when the config is loaded Ctrl Channel is started
    -   Sensequently the Ctrl / Data channel will keep their own sequences for data loss detection
"""
def timeNow():
    return long((datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000) 

def openSocket(address, port, enable_local_loop=1, bind_to_interface="", do_not_load_multicast=False):
    tAddr = socket.getaddrinfo(address, None)[0]
    tsocket = socket.socket(tAddr[0], socket.SOCK_DGRAM)
    tsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tsocket.bind(('', port))
    # print(tAddr, port)
    if not do_not_load_multicast:
        group_bin = socket.inet_pton(tAddr[0], tAddr[4][0])
        mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
        tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, enable_local_loop)
        if (bind_to_interface):
            tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface))
    return tsocket

class jph(object):

    def __init__(self, configURL="", Codifier=""):

        if (os.getenv("JPH_DEBUG", "0")=="1"):
            print("Using env variable JPH_DEBUG") 
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.WARN)
        self.logger=logging.getLogger()

        if (configURL==""):
            configURL=os.getenv("JPH_CONFIG", configURL)
            self.logger.debug("Using env variable JPH_CONFIG=%s", configURL) 
        if (Codifier==""):
            Codifier=os.getenv("JPH_SENSOR", Codifier)
            self.logger.debug("Using env variable JPH_SENSOR=%s", Codifier) 
        self.configURL=configURL
        self.Codifier=str(Codifier)

        self.CtrlSocket=0
        self.DataSocket=0
        self.SensorInterval=0
        self.ConfigTimestamp=0
        self.IsActive=""
        self.SequenceTable={}

        self.loadConfig()
        
    def loadConfig(self):
        try:
            self.configJSON=json.loads(urllib2.urlopen(self.configURL).read())
        except Exception as e:
            self.logger.critical("Failed to JSON config (URL:%s): %s", self.configURL, e)
            raise ValueError(e)

        f=""
        try:
            for s in self.configJSON["Sensors"]:
                if s["Codifier"] == self.Codifier:
                    f=s
                    break
            if f == "":
                raise ValueError("Failed to find sensor (%s)" % self.Codifier)
            self.Sensor=f

            if (self.IsActive==""):
                self.IsActive=self.Sensor["Active"]
            self.ProgramType=self.Sensor["Type"]
        except Exception as e:
            err=("Unexpected JSON error (Codifier:%s): %s" % (self.Codifier, e))
            self.logger.critical(err)
            raise ValueError(err)

        self.ConfigTimestamp=timeNow()

        if (os.getenv("JPH_DEBUG", "0")=="1"):
            self.logger.info("(Re)Starting logging in DEBUG")
            return

        try:
            tst = self.configJSON["Logging"]
        except Exception as e:
            err=("Unexpected JSON error (failed to load field 'Logging')")
            self.logger.critical(err)
            raise ValueError(err)

        try:
            logging.config.dictConfig(self.configJSON["Logging"])
        except Exception as e:
            err=("Unexpected JSON error (processing Logging config): %s" % (e))
            self.logger.critical(err)
            raise Exception(err)

        try:
            f=""
            for l in self.configJSON["Logging"]["loggers"]:
                if l == __name__ + '-' + self.Codifier:
                    f=l
            if f == "":
                for l in self.configJSON["Logging"]["loggers"]:
                    if l == __name__:
                        f=l
            if f == "":
                for l in self.configJSON["Logging"]["loggers"]:
                    if l == "default":
                        f=l
        except Exception as e:
            err=("Unexpected JSON error (processing logger): %s" % (e))
            self.logger.critical(err)
            raise ValueError(err)

        if f == "":
            self.logger.warn("(Re)Starting. No logger found")
        else:
            self.logger=logging.getLogger(f)
            self.logger.info("(Re)Starting %s on logger: %s", __name__ + '-' + self.Codifier, f)

    def getConfig(self):
        return self.configJSON

    def getAllSensors(self):
        return self.configJSON["Sensors"]

    def getSensor(self, Codifier):
        for s in self.configJSON["Sensors"]:
            if s["Codifier"] == Codifier:
                return s
        return None

    def getMySensor(self):
        return self.Sensor

    def getMySensorElement(self, elem):
        if elem in self.Sensor["Sensor"]:
            return self.Sensor["Sensor"][elem]
        return None

    def startCtrl(self, do_not_load_multicast=False):
        if (self.CtrlSocket!=0):
            self.endCtrl()

        try:
            self.CtrlAddress=self.configJSON["Multicast"]["Control-Channel"]["Address"]
            self.CtrlPort=int(self.configJSON["Multicast"]["Control-Channel"]["Port"])
        except Exception as e:
            err=("Unexpected JSON error (processing 'multicast'|'control-channel'): %s" % (e))
            self.logger.critical(err)
            raise ValueError(err)

        try:
            self.KeepAliveInterval=self.Sensor["KeepAliveInterval"] * 1000
        except Exception as e:
            err=("Unexpected JSON error (processing keepAliveInterval'): %s" % (e))
            self.logger.critical(err)
            raise ValueError(err)

        # AUTHOR: Consider programming the logic of looping and binding NIC

        self.CtrlSocket=openSocket(self.CtrlAddress, self.CtrlPort, enable_local_loop=1, do_not_load_multicast=do_not_load_multicast)
        self.CtrlSequence=random.randint(1,2147483647)
        self.sendCtrl(flag='N')

    def endCtrl(self):
        if (self.CtrlSocket==0):
            return
        self.CtrlSocket.close()
        self.CtrlSocket=0

    def startData(self, do_not_load_multicast=False):
        if (self.DataSocket!=0):
            self.endData()

        try:
            self.DataAddress=self.configJSON["Multicast"]["Data-Channel"]["Address"]
            self.DataPort=int(self.configJSON["Multicast"]["Data-Channel"]["Port"])
        except Exception as e:
            err=("Unexpected JSON error (processing 'multicast'|'data-channel'): %s" % (e))
            self.logger.critical(err)
            raise ValueError(err)

        # AUTHOR: Consider programming the logic of looping and binding NIC
        self.DataSocket=openSocket(self.DataAddress, self.DataPort, enable_local_loop=1, do_not_load_multicast=do_not_load_multicast)

    def endData(self):
        if (self.DataSocket==0):
            return
        self.DataSocket.close()
        self.DataSocket=0

    def sendData(self, data, timestamp=0, Codifier="", sequence_packet=False):
        if (self.DataSocket==0):
            # DOUWE if (self.CtrlSocket==0):
            # DOUWE     self.startCtrl(do_not_load_multicast=True)   # remove option from
            self.startData(do_not_load_multicast=True)

        if timestamp==0:
            timestamp=timeNow()
        to=str("@@")

        if Codifier=="":
            Codifier=self.Codifier
        else:
            Codifier=str(Codifier)

        if (sequence_packet):
            sequence=data
            flag = str('n') # TOCHANGE
            packed = struct.pack('I', sequence)
        else:
            if not Codifier in self.SequenceTable:
                self.SequenceTable[Codifier]=random.randint(1,2147483647)
                self.sendData(data=self.SequenceTable[Codifier], timestamp=timestamp, Codifier=Codifier, sequence_packet=True)

            self.SequenceTable[Codifier]+=1
            sequence=self.SequenceTable[Codifier]

            if isinstance(data, unicode):           
                data=str(data)
            if type(data) == type(int()):
                flag = str('i')
                packed = struct.pack('I', data)
            elif isinstance(data, str):
                flag = str('s')
                packed = struct.pack('I%ds' % (len(data),), len(data), data)
            elif isinstance(data, float):
                flag = str('f')
                packed = struct.pack('f', data)
            else:
                raise NotImplementedError("Unknown (unsupported) data type")

        logging.debug("Data-%s : send %s-%s %d %d data:%s", flag, Codifier, to, timestamp, sequence, data)

        packed_data = struct.pack("IQ1s2s2sI%ds" % (len(packed),), sequence, timestamp, flag, Codifier, to, len(packed), packed)

        self.DataSocket.sendto(packed_data, (self.DataAddress, self.DataPort))

    def sendCtrl(self, flag, timestamp=0, to="", timeComponent=0):
        if (self.CtrlSocket==0):
            self.startCtrl(do_not_load_multicast=True)
            # self.startCtrl()

        if to=="":
            to=str("@@")
        else:
            to=str(to[:2])
        flag=str(flag[:1])
        if timestamp==0:
            timestamp=timeNow()
        if timeComponent==0:
            timeComponent=self.ConfigTimestamp
        timeComponent=int(timeComponent)
        logging.debug("Ctrl-%s : send %s-%s %d %d %d %s", flag, self.Codifier, to, timestamp, self.CtrlSequence, timeComponent, self.IsActive)

        data = struct.pack('Q?', timeComponent, self.IsActive)

        packed_data = struct.pack("IQ1s2s2sI%ds" % (len(data),), self.CtrlSequence, timestamp, flag, self.Codifier, to, len(data), data)

        self.CtrlSocket.sendto(packed_data, (self.CtrlAddress, self.CtrlPort))
        if self.CtrlSequence >= 2147483647:
            self.CtrlSequence=0
        else:
            self.CtrlSequence+=1

    def run(self, dataCallback=False, timeCallback=False, ctrlCallback=False):
        if (self.CtrlSocket!=0):
            self.endCtrl()
        while True:
            if (self.CtrlSocket==0):
                self.startCtrl()
            inputs = [self.CtrlSocket]
            if dataCallback:
                self.startData()
                inputs.append(self.DataSocket)
            ctrlNextKeepAlive=0

            if timeCallback:
                try:
                    self.SensorInterval=self.Sensor["SensorInterval"] * 1000
                except Exception as e:
                    err=("Unexpected JSON error (processing SensorInterval'): %s" % (e))
                    self.logger.critical(err)
                    raise ValueError(err)
                makeNextSensorReading = timeNow() + self.SensorInterval
            else:
                makeNextSensorReading = 32503680000000

            forever=True
            while forever:
                t=timeNow()

                if t >= ctrlNextKeepAlive:
                    self.sendCtrl(flag='I')
                    if not self.IsActive:    # DOUWE ! should only apply if there is a data channel active
                         self.logger.debug("Data-  :      Processing currently HALTED.")
                    ctrlNextKeepAlive = t + (self.KeepAliveInterval)

                if t >= makeNextSensorReading:
                    if self.IsActive:
                        try:
                            timeCallback(t)
                        except:
                            self.logger.critical("Unexpected error: %s", sys.exc_info()[0])
                            sys,exit()
                    makeNextSensorReading = t + self.SensorInterval

                timeout=float((max(0.001, (min(makeNextSensorReading, ctrlNextKeepAlive) - t)/1000)))
                readable, writable, exceptional = select.select(inputs, [], [], timeout)
                for s in readable:
                    if s == self.DataSocket:
                        data, sender = self.DataSocket.recvfrom(1500)
                        (sequence, timestamp, flag, source, to, length,), value = struct.unpack('IQ1s2s2sI', data[:28]), data[28:]
                        if flag == 'f':
                            value, = struct.unpack('f', value)
                        elif flag == 'i':
                            value, = struct.unpack('I', value)
                        elif flag == 'n':
                            value, = struct.unpack('I', value)
                        elif flag == 's':
                            (i,), x = struct.unpack("I", value[:4]), value[4:]
                            value = x
                            # can you make value the oputput for preesion command
                        else:
                            raise NotImplementedError("Unknown (unsupported) data type")
                        self.logger.debug("Data-%s : recv %s-%s %d %d (len=%d) data:%s", flag, source, to, timestamp, sequence, length, value)
                        if dataCallback and self.IsActive:
                            dataCallback("Data=", flag, source, to, timestamp, sequence, length, sender, value, None)

                    if s == self.CtrlSocket:
                        data, sender = self.CtrlSocket.recvfrom(1500)
                        (sequence, timestamp, flag, source, to, length,), value = struct.unpack('IQ1s2s2sI', data[:28]), data[28:]
                        self.logger.debug("Ctrl-%s : recv %s-%s %d %d (len=%d)", flag, source, to, timestamp, sequence, length)

                        dataTime, isActive2 = struct.unpack('Q?', value)
                        if (to in (self.Codifier, "@@")):
                            if flag == 'C':
                                self.logger.debug("Ctrl-C - recv %s %s Received request to reload config", source, timestamp)
                                self.loadConfig()
                                self.endCtrl()
                                forever = False;
                                break
                            if flag == 'T':
                                self.logger.debug("Ctrl-T - recv Time info %s (ignore)", dataTime)
                            if flag == 'P':
                                self.logger.debug("Ctrl-P - recv Ping Time info requested for %s", dataTime)
                                self.sendCtrl(flag='T', to=source, timeComponent=dataTime)
                            if flag == 'H':
                                self.logger.debug("Ctrl-H - recv Request to halt sensor (from=%s) (time=%s)", source, timestamp)
                                self.IsActive=False
                                ctrlNextKeepAlive=0
                            if flag == 'S':
                                self.logger.debug("Ctrl-S - recv Request to start sensor (from=%s) (time=%s)", source, timestamp)
                                self.IsActive=True
                                ctrlNextKeepAlive=0
                            if flag in ('I', 'N'):
                                self.logger.debug("Ctrl-I - recv Alive Message %s %s %s", source, dataTime, isActive2)
                                if dataTime > self.ConfigTimestamp and source == self.Codifier:
                                    logging.critical("There is another instance of %s running (time=%s)", self.Codifier, str(dataTime))
                                    sys.exit()

                        if ctrlCallback and self.IsActive:
                            ctrlCallback("Ctrl=", flag, source, to, timestamp, sequence, length, sender, dataTime, isActive2)
