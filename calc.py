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
Codifier="PA"

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
#r.hget(source, "DPacketsLost", 0)

def jphlookup(var):
    s=var.find("|")
    if s > 0:
        field=var[s+1:]
        var=var[:s]
        s=field.find("|")
        if s > 0:
            cache=field[:s]
            field=field[s+1:]
        else:
            cache="redis"
    else:
        cache="redis"
        field="Value"
    var=var.strip()
    cache=cache.strip()
    field=field.strip()
    if cache=='redis':
        return str(r.hget(var, field))
    if cache=='config':
        return str(channel.getSensor(var)[field])
    return str(None)

def jphme(var):
    new=""
    s=var.find("{{")
    if s > 0:
        e=var.find("}}", s)
        if e > 0:
            return var[:s] + jphlookup(var[s+2:e]) + jphme(var[e+2:])
        return var
    return var

class CalcHandler(object):

    def __init__(self):
        self.Counter=0

    def Calculate(self, Timestamp):
        filename="custom/" + channel.getMySensorElement("python")
        with open(filename, 'r') as fd:
            code=fd.read()
        exec(jphme(code))
        self.Counter+=1
        channel.sendData(self.Counter)

if __name__ == '__main__':
 
    channel=jph.jph(configURL=configURL, Codifier=Codifier)
    handler=CalcHandler()

    channel.logger.debug("Startup Redis")
    try:
        r=redis.Redis()
    except Exception as e:
        channel.logger.critical("Failed to connect to Redis: (%s)", e)
        sys.exit()

    channel.run(timeCallback=handler.Calculate)
