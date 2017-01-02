from flask import Flask, url_for, render_template, Response, jsonify
from flask_redis import FlaskRedis

import urllib2
import json
import sys
import time
import struct
import random
import jph

# ----- DOUWE : Review this code using jphconfig housekeeping
app = Flask(__name__)
r=FlaskRedis(app) 
app.config['TEMPLATES_AUTO_RELOAD'] = True

#
# ---- Load from config file
#
configURL="file:static/jphmonitor.json2"
Codifier="CK"
channel=jph.jph(configURL=configURL, Codifier=Codifier)

@app.route('/')
def hello_world():
    return 'Fuck you, World! - Be Nice - no need to be a cunt'

@app.route('/sensor/')
@app.route('/sensor/<Codifier>')
def show_sensor(Codifier=None):
    a=[]
    # sensor="C1"
    if (Codifier==None):
        for sensors in channel.getAllSensors():
            if (r.hexists(sensors["Codifier"], "Codifier")):
                a.append(r.hgetall(sensors["Codifier"]))
            else:
                p={}
                p["Codifier"]=sensors["Codifier"]
                a.append(p)
    else:
        if (r.hexists(Codifier, "Codifier")):
            a.append(r.hgetall(Codifier))
        else:
            if (channel.getSensor(Codifier) == None):
                return "Please provide a valid Sensor Codifier"
            p={}
            p["Codifier"]=Codifier
            a.append(p)
    return (Response(response=json.dumps(a), status=200, mimetype="application/json"))

@app.route('/sensors/')
def sensors():
    return render_template('sensors.html', sensors = channel.getAllSensors())

@app.route('/sensorinfo/<Codifier>')
def sensorinfo(Codifier):
    return render_template('sensorinfo.html',
            sensor=channel.getSensor(Codifier),
            redis=r.hgetall(Codifier),
            sensordetail=json.dumps(channel.getSensor(Codifier))
            )

@app.route('/sensormsg/<Codifier>/<flag>')
def sensormsg(Codifier, flag):
    print(Codifier, flag)
    channel.sendCtrl(to=Codifier, flag=flag)
    return "Message send"

@app.route('/toggle/<Codifier>')
def toggle(Codifier):

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
#         seq = random.randint(1,2147483647)
#         seq_packed = struct.pack('I', seq)
# ???        jphconfig.sendControlChannel(t, c, m, seq_packed)
    else:
        a="no data"
    return a

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
