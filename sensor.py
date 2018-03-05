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
import json

# -------------
# Globals
# -------------
configURL="file:static/config.json"
Codifier=""
DevelMode=False

# -------------
# Read Startup Parameters
# -------------
def usage():
    print("Usage: -u <url>", __file__)
    print("\t-u <url> : load the JSON configuration from a url")
    print("\t-c <code>: The Sensor that this program needs to manage") 

try:
    opts, args = getopt.getopt(sys.argv[1:], "hu:c:Z", ["help", "url=", "code="])
    for opt, arg in opts:
        if opt in ("-h", "help"):
            raise
        elif opt in ("-u", "--url"):
            configURL=arg
        elif opt in ("-c", "--code"):
            Codifier=arg
        elif opt in ("-Z"):
            DevelMode=True
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
class PythonNinja(object):
    # These two routines allow you to override sensor data into a text file for scripting 
# or writing to files
    def jphlookup(self, var):
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

    def jphninja(self, var):
        s=var.find("{{")
        if s > 0:
            e=var.find("}}", s)
            if e > 0:
                return var[:s] + self.jphlookup(var[s+2:e]) + self.jphninja(var[e+2:])
        return var

    def run(self, Timestamp, command="", number=None):
        t1=time.time() * 1000
        filename=channel.getMySensorElement("Filename")
        with open(filename, 'r') as fd:
            code=fd.read()
        exec(self.jphninja(code))
        t2=time.time() * 1000
        channel.sendData(t2-t1)
        return jph.STATE.GOOD

class TempLinux(object):
    def run(self, Timestamp, command="", number=None):
        try:
            channel.sendData(float(os.popen(self.cmd).read())/1000)
        except AttributeError:
            self.cmd= ("/bin/cat " + channel.getMySensorElement("Pipe"))
            channel.sendData(float(os.popen(self.cmd).read())/1000)
        return jph.STATE.GOOD

class failsafeReader(object):
    def run(self, Timestamp, command="", number=None):
        # try:
        s=channel.getMySensorElement("URL")
        response=requests.get(s, timeout=(2.0, 10.0))
        if response.headers["content-type"] != "application/json":
            channel.logger.error("Unexpected response from Arduino")
            raise WrongContent(response=response)
        else:
            if (len(response.text) > 1):
                ### !!! BAD BODGE The input data is malformed, fix it with this 'replace()'' clause :(
                response2 = response.text.replace("inf", "0")
                json_data = json.loads(response2.replace(",]}","]}"))
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
    def __init__(self):
        self.allfood=True
    
    def phobya2temp(self, voltageOut):
        ohm=(5-voltageOut)/voltageOut*16800/1000
        temp=(0.0755*math.pow(ohm,2))-4.2327*ohm+60.589
        channel.logger.debug("Sensor: Voltage: %s, Temp: %s", voltageOut, temp)
        return temp

    def read(self, pin, theCodefier):
        channel.logger.debug("Sensor: Reading pin: %d", pin)
        v = adc.read_voltage(pin)
        if v!=0:
            d = self.phobya2temp(v)
            y = {}
            y["value"]=d
            y["voltage"]=v
            l=json.dumps(y)
            if (theCodefier==""):
                channel.sendData(data=l, isJson=True)
            else:
                channel.sendData(data=l, Codifier=theCodefier, isJson=True)
        else:
            self.allgood=False

    def run(self, Timestamp, command="", number=None):
        self.allgood=True
        self.read(int(channel.getMySensorElement("Pin")), "")
        for proxy in channel.getMySensorElement("Proxy"):
            self.read(int(proxy["Pin"]), str(proxy["Codifier"]))
        if self.allgood:
            return jph.STATE.GOOD
        return jph.STATE.NOREADING

class ADAfruitReader(object):
    def run(self, Timestamp, command="", number=None):
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
    def run(self, Timestamp, command="", number=None):
        u=channel.getMySensorElement("URL")
        s=channel.getMySensorElement("Server")
        try:
            response=requests.get(u, timeout=(2.0, 10.0))
        except: 
            channel.logger.error("Unexpected Dwarfpool error: %s", sys.exc_info()[0])
        else: 
            if response.headers["content-type"] != "application/json":
                channel.logger.error("Unexpected content.type from Dwarfpool")
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

    def run(self, Timestamp, command="", number=None):
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
        self.nodes=[]
        self.sensors=[]

        # build an array of the requested zwave items
        n=channel.getMySensorElement("node")
        i=channel.getMySensorElement("index")
        a=channel.getMySensorElement("instance")
        c=Codifier
        self.sensors.append((n,i,a,c))
        for proxy in channel.getMySensorElement("Proxy"):
            n=int(proxy["node"])
            i=int(proxy["index"])
            a=int(proxy["instance"])
            c=proxy["Codifier"]
            self.sensors.append((n,i,a,c))
        self.sensors.sort(key=lambda tup: tup[0])
        channel.logger.debug("Zwave components: %s", self.sensors)

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
                # sys.stdout.write('.')
                # sys.stdout.flush()
                time.sleep(1.0)

        if self.network.state<self.network.STATE_AWAKED:
            channel.logger.error("Zwave Network is not awake but continue anyway")

        for node in self.network.nodes:
            channel.logger.debug("%s - Product name / id / type : %s / %s / %s", self.network.nodes[node].node_id, self.network.nodes[node].product_name, self.network.nodes[node].product_id, self.network.nodes[node].product_type)
            channel.logger.debug("%s - Name : %s", self.network.nodes[node].node_id,self.network.nodes[node].name)
            channel.logger.debug("%s - Manufacturer name / id : %s / %s", self.network.nodes[node].node_id, self.network.nodes[node].manufacturer_name, self.network.nodes[node].manufacturer_id)
            channel.logger.debug("%s - Version : %s", self.network.nodes[node].node_id, self.network.nodes[node].version)
            # # print("%s - Command classes : %s" % (network.nodes[node].node_id,network.nodes[node].command_classes_as_string))
            channel.logger.debug("%s - Capabilities : %s", self.network.nodes[node].node_id,self.network.nodes[node].capabilities)

            self.nodes.append(self.network.nodes[node].node_id)
        channel.logger.debug("nodes found: %s", self.nodes)
                
    def run(self, Timestamp, command="", number=None):
        for node in self.nodes:
            for val in self.network.nodes[node].get_sensors():
                channel.logger.debug("value: %s", val)
                channel.logger.debug("node/name/index/instance : %s/%s/%s/%s", node,
                     self.network.nodes[node].name,
                     self.network.nodes[node].values[val].index,
                     self.network.nodes[node].values[val].instance)
                channel.logger.debug("%s/%s %s %s", self.network.nodes[node].values[val].label,
                     self.network.nodes[node].values[val].help,
                     self.network.nodes[node].get_sensor_value(val),
                     self.network.nodes[node].values[val].units)

                for looper in self.sensors:
                    (n, i, a, c)=looper
                    if n==node and i==self.network.nodes[node].values[val].index:
                        ans=self.network.nodes[node].get_sensor_value(val)
                        # print("found", c, ans)
                        channel.sendData(data=ans, Codifier=str(c))
                        break
        return jph.STATE.GOOD

class controlSensor(object):
    def __init__(self):
        try:
            self.value=float(channel.getMySensorElement("Default"))
        except:
            self.value=0
        print("I initialized", self.value)

    def run(self, Timestamp, command="", number=None):
        if command=="A":
            if number==None:
                channel.logger.error("Command A expects target value")
            else:
                self.value=number
        if command=="E":
            if number==None:
                channel.logger.error("Command E expects step value")
            else:
                self.value=self.value+number
        channel.sendData(data=self.value)

class fanControl(object):
    def __init__(self):
        self.value = 100
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)   # This example uses the BCM pin numbering
        GPIO.setup(25, GPIO.OUT) # GPIO 25 is set to be an output.
        GPIO.setup(24, GPIO.OUT)
        GPIO.output(24, 0)
        self.pwm = GPIO.PWM(25, 10000)  
        self.pwm.start(self.value)

    def run(self, Timestamp, command="", number=None):
        if command=="A":
            if number==None:
                channel.logger.error("Command A expects target value")
            else:
                self.value=number
        if command=="E":
            if number==None:
                channel.logger.error("Command E expects step value")
            else:
                self.value=self.value+number
        if command!="":
            if ( self.value < 0 ):
                self.value=0
            if ( self.value > 100 ):
                self.value=100
            self.pwm.ChangeDutyCycle(self.value)
        channel.sendData(data=self.value)

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
        from math import log
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
    if type == "fanControl":
        import RPi.GPIO as GPIO

    c=eval(type + '()')
    channel.run(timeCallback=c.run )

