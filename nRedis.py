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
configURL="file:static/jphmonitor.json2"
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

    def publish(self, Timestamp):
        channel.sendData(self.Counter)
        self.Counter=0

    def updateData(self, chnl, flag, source, to, timestamp, sequence, length, sender, data, isActive):
        if chnl[:1] == "D":
            if (flag == 'n'):
                self.LastDataSequence[source]=sequence
                r.hset(source, "DPacketsLost", 0)
                r.hset(source, "DPacketResetTime", timestamp)
                self.Counter+=1
                channel.logger.debug("%d %s%s %s Reset=%d", timestamp, chnl, flag, source, sequence)
            else:
                if source in self.LastDataSequence:
                    diff=sequence - self.LastDataSequence[source]
                    if diff != 1:
                        channel.logger.warning("%d packets lost on Data channel %s", diff, source)
                        r.hincrby(source, "DPacketsLost", diff)
                self.LastDataSequence[source]=sequence

                r.hset(source, "Codifier",source)
                r.hset(source, "Value",data)
                r.hset(source, "DTimestamp",timestamp)
                self.Counter+=3
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

    channel.run(dataCallback=handler.updateData, timeCallback=handler.publish)
