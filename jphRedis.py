#!/usr/bin/env python
from __future__ import print_function, absolute_import, division, nested_scopes, generators, unicode_literals
import sys
import getopt
import struct
import jph
import os
import redis
import time

# -------------
# Globals
# -------------
configURL="file:static/config.json"
Codifier="R1"

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
class RedisHandler(object):

    def __init__(self):
        self.Counter=0
        self.LastDataSequence={}
        self.LastCtrlSequence={}
        self.LastTime=0
        self.LostMessageRepeat={}
        self.LostMessageLastTime={}
        self.LostMessageEnabled={}

    def publish(self, Timestamp):
        if self.LastTime!=0:   # Skip the first time to build up an average
            t=jph.timeNow()
            a=self.Counter*(60/((t-self.LastTime)/1000))
            channel.sendData(int(a))
        self.LastTime=jph.timeNow()
        self.Counter=0

    def updateData(self, chnl, flag, source, to, timestamp, sequence, length, sender, data, isActive):
        r.hset(source, "Codifier", source)
        if (flag == 'n'):
            self.LastDataSequence[source]=sequence
            r.hset(source, "DPacketsLost", 0)
            r.hset(source, "DResetTime", timestamp)
            self.Counter+=3
            channel.logger.debug("%d %s%s %s Reset=%d", timestamp, chnl, flag, source, sequence)
        else:
            if source in self.LastDataSequence:
                diff=sequence - self.LastDataSequence[source]
                if diff != 1:
                    if source in self.LostMessageRepeat:    
                        t=jph.timeNow()
                        sincelast=((t-self.LostMessageLastTime[source]) / 1000)
                        print(source, "sincelast:", sincelast, self.LostMessageRepeat[source], self.LostMessageEnabled[source])

                        if sincelast<(60*60):
                            self.LostMessageRepeat[source]+=1
                            if (self.LostMessageRepeat[source]>2): 
                                if self.LostMessageEnabled[source]:
                                    self.LostMessageEnabled[source]=False
                                    channel.logger.warning("Lost messages for %s surpressed for 1 hour (too many)", source)
                        else:
                            if not self.LostMessageEnabled[source]:
                                channel.logger.warning("%d Lost messages for %s repressed. (restart)", self.LostMessageRepeat[source], source)
                            self.LostMessageRepeat[source]=0
                            self.LostMessageEnabled[source]=True

                    else:
                        self.LostMessageEnabled[source]=True
                        self.LostMessageRepeat[source]=0

                    if self.LostMessageEnabled[source]:
                        self.LostMessageLastTime[source]=jph.timeNow()
                        channel.logger.warning("%d %s%s %s Lost=%d", timestamp, chnl, flag, source, (diff-1))
                    r.hincrby(source, "DPacketsLost", (diff-1))
                    self.Counter+=1

            self.LastDataSequence[source]=sequence
            r.hset(source, "Value",data)
            r.hset(source, "DTimestamp",timestamp)
            self.Counter+=3
            channel.logger.debug("%d %s%s %s Data=%d", timestamp, chnl, flag, source, data)

    def updateCtrl(self, chnl, flag, source, to, timestamp, sequence, length, sender, data, isActive):
        r.hset(source, "Codifier", source)
        if (flag == 'N'):
            self.LastCtrlSequence[source]=sequence
            r.hset(source, "CPacketsLost", 0)
            r.hset(source, "CResetTime", timestamp)
            self.Counter+=3
            channel.logger.debug("%d %s%s %s Reset=%d", timestamp, chnl, flag, source, sequence)
        else:
            if source in self.LastCtrlSequence:
                diff=sequence - self.LastCtrlSequence[source]
                if diff != 1:
                    channel.logger.warning("%d %s%s %s Lost=%d", timestamp, chnl, flag, source, (diff-1))
                    r.hincrby(source, "CPacketsLost", (diff-1))
                    self.Counter+=1
            self.LastCtrlSequence[source]=sequence

            if flag == 'P':
                r.hset(source, "PTimestamp", timestamp)
                r.hset(source, "PRequest", data)
            if flag == 'T':
                r.hset(source, "TRequest", data)
                r.hset(source, "TTimestamp", timestamp)
                r.hset(source, "TDuration", timestamp-data)
            if flag == 'H':
                r.hset(source, "HTimestamp", timestamp)
            if flag == 'S':
                r.hset(source, "STimestamp", timestamp)
            if flag == 'I':
                r.hset(source, "ITimestamp", timestamp)
                r.hset(source, "IsActive", isActive)
            if flag == 'C':
                r.hset(source, "CTimestamp", timestamp)

            channel.logger.debug("%d %s%s %s Data=%d", timestamp, chnl, flag, source, data)

if __name__ == '__main__':
 
    channel=jph.jph(configURL=configURL, Codifier=Codifier)
    handler=RedisHandler()

    channel.logger.debug("Startup Redis")
    try:
        r=redis.Redis()
    except Exception as e:
        channel.logger.critical("Failed to connect to Redis: (%s)", e)
        sys.exit()

    channel.run(dataCallback=handler.updateData, timeCallback=handler.publish, ctrlCallback=handler.updateCtrl)
