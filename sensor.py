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
        return jph.STATE.GOOD

class TempLinux(object):
    def run(self, Timestamp):
        try:
            channel.sendData(float(os.popen(self.cmd).read())/1000)
        except AttributeError:
            self.cmd= ("/bin/cat " + channel.getMySensorElement("Pipe"))
            channel.sendData(float(os.popen(self.cmd).read())/1000)
        return jph.STATE.GOOD

class failsafeReader(object):
    def run(self, Timestamp):
        # try:
        s=channel.getMySensorElement("URL")
        response=requests.get(s, timeout=(2.0, 10.0))
        if response.headers["content-type"] != "application/json":
            channel.logger.error("Unexpected response from Arduino")
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
                return jph.STATE.GOOD
            else:
                channel.logger.error("Did not receive a response from Arduino")
        return jph.STATE.FAILED

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
        return jph.STATE.GOOD

class ADAfruitReader(object):
    def run(self, Timestamp):
        h, v = Adafruit_DHT.read_retry(Adafruit_DHT.AM2302, int(channel.getMySensorElement("Pin")))
        if h is None and v is None:
            channel.logger.error("Adafruit_DHT sensor reading returned no data")
            return jph.STATE.FAILED
        else:
            channel.sendData(data=v)
            for proxy in channel.getMySensorElement("Proxy"):
                 channel.sendData(data=h, Codifier=str(proxy["Codifier"]))
            return jph.STATE.GOOD

class DwarfpoolReader(object):
    def __init__(self):
        self.tl=0
    def run(self, Timestamp):
        u=channel.getMySensorElement("URL")
        s=channel.getMySensorElement("Server")
        response=requests.get(u, timeout=(2.0, 10.0))
        if response.headers["content-type"] != "application/json":
            channel.logger.error("Unexpected response from Dwarfpool")
            raise WrongContent(response=response)
        else:
            if (len(response.text) > 1):
                j=json.loads(response.text)
                try:
                    d=j["workers"][s]
                except:
                    channel.logger.error("Dwarfpool server not found: %s", s)
                else:
                    tp=datetime.strptime(d["last_submit"], "%a, %d %b %Y %H:%M:%S %Z")
                    tn=(tp - datetime(1970,1,1)).total_seconds()
                    if (tn>self.tl):
                        self.tl=tn
                        channel.sendData(data=d["hashrate"])
                        for proxy in channel.getMySensorElement("Proxy"):
                            channel.sendData(data=d["hashrate_calculated"], Codifier=str(proxy["Codifier"]))
                        return jph.STATE.GOOD
                    else:
                        return jph.STATE.NOREADING
            else:
                channel.logger.error("Did not receive a response from Dwarfpool")
        return jph.STATE.FAILED

class NestReader(object):
    def __init__(self):
        try:
            file=channel.getMySensorElement("Password")
            line=open(os.path.expanduser(file)).read().splitlines()
            self.nuser=line[0]
            self.npass=line[1]
        except:
            channel.logger.critical("Failed to read Nest Password File")
            sys.exit()
        self.loadnest=False

    def run(self, Timestamp):
        if not self.loadnest:
            try:
                self.napi = nest.Nest(self.nuser, self.npass)
                self.loadnest=True
            except Exception as e:
                channel.logger.critical("Can not connect to Nest")
                sys.exit()
        nestAway=True;
        nestTemp=-80;
        nestHumidity=-1;
        nestTempOutside=-80;
        nestHumiOutside=-1;
        try:
            for structure in self.napi.structures:
                nestAway=structure.away
                for device in structure.devices:
                    nestTemp=float(device.temperature)
                    nestHumidity=float(device.humidity)
                    nestTarget=float(device.target)
            structure=self.napi.structures[0]
            nestTempOutside=structure.weather.current.temperature
            nestHumiOutside=structure.weather.current.humidity
        except:
            channel.logger.error("Unexpected Nest error: %s", sys.exc_info()[0])
            return jph.STATE.FAILED
        # print("Away: %s, Temp: %f, Humidity: %f" % (str(nestAway), nestTemp, nestHumidity))
        if (nestTemp==-80):
            self.loadnest=False
            channel.logger.error("Unknown Error reading from Nest")
            return jph.STATE.FAILED
        if nestAway:
            nestAway=1
        else:
            nestAway=0
        channel.sendData(data=eval(channel.getMySensorElement("Field")))
        for proxy in channel.getMySensorElement("Proxy"):
            channel.sendData(data=eval(proxy["Field"]), Codifier=str(proxy["Codifier"]))
        return jph.STATE.GOOD

class ZwavePower(object):
    def __init__(self):
        os.chdir(os.path.expanduser("~/zwave"))
        path=os.getcwd()
        device=str("/dev/ttyACM0")
        c_path=os.path.expanduser("~/zwave/config")
        options = ZWaveOption(device, config_path=str(c_path),  user_path=str("."), cmd_line=str(""))
        options.lock()
       
        # print("------------------------------------------------------------")
        # print("Waiting for network awaked : ")
        # print("------------------------------------------------------------")
        self.network = ZWaveNetwork(options, log=None, autostart=True)
        for i in range(0,300):
            if self.network.state>=self.network.STATE_AWAKED:
                break
            else:
                time.sleep(1.0)
        if self.network.state<self.network.STATE_AWAKED:
            channel.logger.error("Zwave Network is not awake but continue anyway")

        for node in self.network.nodes:
            # print("%s - Product name / id / type : %s / %s / %s" % (self.network.nodes[node].node_id,self.network.nodes[node].product_name, self.network.nodes[node].product_id, self.network.nodes[node].product_type))
            # print("%s - Name : %s" % (self.network.nodes[node].node_id,self.network.nodes[node].name))
            # print("%s - Manufacturer name / id : %s / %s" % (self.network.nodes[node].node_id,self.network.nodes[node].manufacturer_name, self.network.nodes[node].manufacturer_id))
            # print("%s - Version : %s" % (self.network.nodes[node].node_id, self.network.nodes[node].version))
            #print("%s - Command classes : %s" % (network.nodes[node].node_id,network.nodes[node].command_classes_as_string))
            # print("%s - Capabilities : %s" % (self.network.nodes[node].node_id,self.network.nodes[node].capabilities))
            if "FGWPE Wall Plug"==self.network.nodes[node].product_name:
                mynodeid=self.network.nodes[node].node_id
                self.mynode=ZWaveNode(mynodeid, self.network)
                self.mynode.set_field(str("name"), str("JPH"))
                self.xnode=node
                break
    def run(self, Timestamp):
        self.mynode.refresh_info()
        Power1=-1;
        Power2=-1;
        Energy=-1
        withErrors=False
        for val in self.network.nodes[self.xnode].get_sensors() :
            #print("node/name/index/instance : %s/%s/%s/%s" % (node,
            # network.nodes[node].name,
            # network.nodes[node].values[val].index,
            # network.nodes[node].values[val].instance))
            #print("%s/%s %s %s" % (network.nodes[node].values[val].label,
            # network.nodes[node].values[val].help,
            # network.nodes[node].get_sensor_value(val),
            # network.nodes[node].values[val].units))
            if self.network.nodes[self.xnode].values[val].index==4:
                Power1=self.network.nodes[self.xnode].get_sensor_value(val)
            if self.network.nodes[self.xnode].values[val].index==8:
                Power2=self.network.nodes[self.xnode].get_sensor_value(val)
            if self.network.nodes[self.xnode].values[val].index==0:
                Energy=self.network.nodes[self.xnode].get_sensor_value(val)

        if (Power1==-1 or Power2==-1 or Energy==-1):
            channel.logger.error("Failed to obtain Zwave values")
            withErrors=True
        channel.logger.debug("Values: power(%0.2f/%0.2f)W energy(%0.2f)kWh" % (Power1, Power2, Energy))
        channel.sendData(data=eval(channel.getMySensorElement("Field")))
        for proxy in channel.getMySensorElement("Proxy"):
            channel.sendData(data=eval(proxy["Field"]), Codifier=str(proxy["Codifier"]))
        if withErrors:
            return jph.STATE.WITHERRORS
        return jph.STATE.GOOD

if __name__ == '__main__':

    channel=jph.jph(configURL=configURL, Codifier=Codifier)

    type=channel.getMySensor()["Type"]
    if type == "ADAfruitReader":
        import Adafruit_DHT
    if type == "DwarfpoolReader":
        import requests
        import json
        from datetime import datetime
        # from dateutil import tz
    if type == "NestReader":
        import nest
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
    if type == 'ZwavePower':
        import openzwave
        from openzwave.node import ZWaveNode
        from openzwave.network import ZWaveNetwork
        from openzwave.option import ZWaveOption



    c=eval(type + '()')
    channel.run(timeCallback=c.run )

