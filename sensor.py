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

# These two routines allow you to override sensor data into a text file for scripting 
# or writing to files
def jphlookup(var):
    s=var.find("|")
    if s > 0:
        field=var[s+1:]
        var=var[:s]
        s=field.find("|")
        if s > 0:
            cache=field[:s].strip()
            field=field[s+1:]
        else:
            cache="redis"
    else:
        cache="redis"
        field="Value"
    if cache=='redis':
        return str(r.hget(var.strip(), field.strip()))
    if cache=='config':
        return str(channel.getSensor(var.strip())[field.strip()])
    return str(None)

def jphninja(var):
    s=var.find("{{")
    if s > 0:
        e=var.find("}}", s)
        if e > 0:
            return var[:s] + jphlookup(var[s+2:e]) + jphninja(var[e+2:])
    return var

#
# by making a Sensor a class you can store local variables
# and make a function to check the sensor every x seconds but only update the 
# data if the sensor changed within a specific tollerance
# 
# Also allow for enhanced inequiry capabilities using a peer-to-peer future prototcol
class PythonNinja(object):
    def run(self, Timestamp):
        t1=time.time() * 1000
        filename=channel.getMySensorElement("Filename")
        with open(filename, 'r') as fd:
            code=fd.read()
        exec(jphninja(code))
        t2=time.time() * 1000
        channel.sendData(t2-t1)

class TempLinux(object):
    def run(self, Timestamp):
        try:
            channel.sendData(float(os.popen(self.cmd).read())/1000)
        except AttributeError:
            self.cmd= ("/bin/cat " + channel.getMySensorElement("Pipe"))
            channel.sendData(float(os.popen(self.cmd).read())/1000)

class failsafeReader(object):
    def run(self, Timestamp):
        # try:
        s=channel.getMySensorElement("URL")
        response=requests.get(s, timeout=(2.0, 10.0))
        if response.headers["content-type"] != "application/json":
            raise WrongContent(response=response)
        else:
            if (len(response.text) > 1):
                ### !!! BAD BODGE The input data is malformed, fix it with this 'replace()'' clause :(
                json_data = json.loads(response.text.replace(",]}","]}"))
                v=json_data[channel.getMySensorElement("Field")]
                channel.sendData(data=v, Codifier="")
                for proxy in channel.getMySensorElement("Proxy"):
                    v=json_data[proxy["Field"]]
                    code=str(proxy["Codifier"])
                    channel.sendData(data=v, Codifier=code)

class ADCpiReader(object):
    def phobya2temp(self, voltageOut):
        ohm=(5-voltageOut)/voltageOut*16800/1000
        temp=(0.0755*math.pow(ohm,2))-4.2327*ohm+60.589
        return temp

    def run(self, Timestamp):
        v = adc.read_voltage(int(channel.getMySensorElement("Pin")))
        channel.sendData(data=self.phobya2temp(v))
        for proxy in channel.getMySensorElement("Proxy"):
            v = adc.read_voltage(int(proxy["Pin"]))
            channel.sendData(data=self.phobya2temp(v), Codifier=str(proxy["Codifier"]))

class ADAfruitReader(object):
    def run(self, Timestamp):
        h, v = Adafruit_DHT.read_retry(Adafruit_DHT.AM2302, int(channel.getMySensorElement("Pin")))
        if h is None and v is None:
            print("SENSORS RETURN NO VALUES BRO")
        else:
            channel.sendData(data=v)
            for proxy in channel.getMySensorElement("Proxy"):
                 channel.sendData(data=h, Codifier=str(proxy["Codifier"]))

class DwarfpoolReader(object):
    def __init__(self):
        self.tl=0
    def run(self, Timestamp):
        u=channel.getMySensorElement("URL")
        s=channel.getMySensorElement("Server")
        response=requests.get(u, timeout=(2.0, 10.0))
        if response.headers["content-type"] != "application/json":
            raise WrongContent(response=response)
        else:
            if (len(response.text) > 1):
                j=json.loads(response.text)
                d=j["workers"][s]
                tp=datetime.strptime(d["last_submit"], "%a, %d %b %Y %H:%M:%S %Z")
                tn=(tp - datetime(1970,1,1)).total_seconds()
                if (tn>self.tl):
                    self.tl=tn
                    channel.sendData(data=d["hashrate"])
                    for proxy in channel.getMySensorElement("Proxy"):
                        channel.sendData(data=d["hashrate_calculated"], Codifier=str(proxy["Codifier"]))

if __name__ == '__main__':

    channel=jph.jph(configURL=configURL, Codifier=Codifier)

    type=channel.getMySensor()["Type"]
    if type == "ADAfruitReader":
        import Adafruit_DHT
    if type == "DwarfpoolReader":
        import requests
        import json
        from datetime import datetime
        from dateutil import tz
    if type == "failsafeReader":
        import requests
        import json
    if type == "PythonNinja":
        import redis
        r=redis.Redis()
    if type == "ADCpiReader":
        sys.path.append("/home/jphmonitor")
        sys.path.append('/home/jphmonitor/ABElectronics_Python_Libraries/ADCPi')
        from ABE_ADCPi import ADCPi
        from ABE_helpers import ABEHelpers
        i2c_helper = ABEHelpers()
        bus = i2c_helper.get_smbus()
        adc = ADCPi(bus, 0x68, 0x69, 12)

    c=eval(type + '()')
    channel.run(timeCallback=c.run )

