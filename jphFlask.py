from flask import Flask, url_for, render_template, Response, jsonify
from flask_redis import FlaskRedis

import urllib2
import json
import sys
import time
import struct
import random
import jph

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

r=FlaskRedis(app) 

configURL="file:static/config.json"
Codifier="CF"
channel=jph.jph(configURL=configURL, Codifier=Codifier)

@app.route('/')
def sensors():
    return render_template('dashboard.html', sensors = channel.getAllSensors())

@app.route('/sensor/')
@app.route('/sensor/<Codifier>')
def show_sensor(Codifier=None):
    a=[]
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
    return (Response(response=json.dumps(a),
            status=200, mimetype="application/json"))


@app.route('/sensorinfo/<Codifier>')
def sensorinfo(Codifier):
    return render_template('sensorinfo.html',
            sensor=channel.getSensor(Codifier),
            redis=r.hgetall(Codifier),
            sensordetail=json.dumps(channel.getSensor(Codifier)))

@app.route('/sensormsg/<Codifier>/<flag>')
def sensormsg(Codifier, flag):
    p={}
    t=jph.timeNow()
    p["Codifier"]=Codifier
    p["Flag"]=flag
    p["Timestamp"]=t
    channel.sendCtrl(to=Codifier, flag=flag, timeComponent=t)
    return (Response(response=json.dumps(p),
            status=200, mimetype="application/json"))

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
