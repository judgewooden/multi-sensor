from flask import Flask, url_for, render_template, Response, jsonify
from flask_redis import FlaskRedis

import urllib2
import json
import sys
import time
import struct
import random
import jphconfig

# ----- DOUWE : Review this code using jphconfig housekeeping
app = Flask(__name__)
configurl="file:static/jphmonitor.json2"
r=FlaskRedis(app) 

app.config['TEMPLATES_AUTO_RELOAD'] = True

#
# ---- Load from config file
#
try:
    configJSON=json.loads(urllib2.urlopen(configurl).read())
except Exception as e:
    print (e)
    print("Failed to parse json", configurl)
    sys.exit()

ctrlSocket=jphconfig.openControlChannel(
configJSON["Multicast"]["Control-Channel"]["Address"],
configJSON["Multicast"]["Control-Channel"]["Port"])
ctrlNextKeepAlive=0

@app.route('/')
def hello_world():
    return 'Fuck you, World! - Be Nice - no need to be a cunt'

@app.route('/sensor/')
@app.route('/sensor/<sensor>')
def show_sensor(sensor=None):
    a=[]
    # sensor="C1"
    if (sensor==None):
        for sensors in configJSON["Sensors"]:
            if (r.hexists(sensors["Codifier"], "Codifier")):
                a.append(r.hgetall(sensors["Codifier"]))
            else:
                p={}
                p["Codifier"]=sensors["Codifier"]
                a.append(p)
    else:
        if (r.hexists(sensor, "Codifier")):
            a.append(r.hgetall(sensor))
        else:
            for sensors in configJSON["Sensors"]:
                if (sensors["Codifier"]==sensor):
                    p={}
                    p["Codifier"]=sensors["Codifier"]
                    a.append(p)
                break

    return (Response(response=json.dumps(a), status=200, mimetype="application/json"))

@app.route('/sensors/')
def sensors():
    return render_template('sensors.html', sensors = configJSON["Sensors"])

@app.route('/sensorinfo/<sensor>')
def sensorinfo(sensor):
    c=str(sensor)
    if (sensor!=None):
        for x in configJSON["Sensors"]:
            if (x["Codifier"]==c):
                p=(r.hgetall(c))
                if "Sensor" in x:
                    y=json.dumps(x["Sensor"])
                else:
                    y="None"
                return render_template('sensorinfo.html', sensor=x, redis=p, sensordetail=y)
    return "Please provide a valid Sensor Codifier"

@app.route('/toggle/<sensor>')
def xhr(sensor):

    c=str(sensor)
    if c != "":
        # Consider what to do with proxy sensors
        for p in configJSON["Sensors"]:
            if p["Codifier"] == c:
                if p["Sensor"]["Type"] == "RedisLoader":
                    return c + " denied"
                if p["Sensor"]["Type"] == "Proxy":
                    c=str(p["Sensor"]["Codifier"])
                break
        else:
            return c + " not found"

        # Check thoe current status and toggle it .....
        s=r.hget(c,"IsActive")
        if (s=="True"):
            m="H"
            a=c + " Halt"
        else:
            m="S"
            a=c + " Start"
        t=int(time.time()) 
        seq = random.randint(1,2147483647)
        seq_packed = struct.pack('I', seq)
        jphconfig.sendControlChannel(t, c, m, seq_packed)
    else:
        a="no data"
    return a

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
