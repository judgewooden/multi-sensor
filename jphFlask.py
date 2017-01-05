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
MyCodifier="CF"
channel=jph.jph(configURL=configURL, Codifier=MyCodifier)

@app.route('/')
def sensors():
    return render_template('dashboard.html', sensors = channel.getAllSensors())

@app.route('/sensor/')
@app.route('/sensor/<codifier>')
def show_sensor(codifier=None):
    a=[]
    if (codifier==None):
        for sensors in channel.getAllSensors():
            if (r.hexists(sensors["Codifier"], "Codifier")):
                a.append(r.hgetall(sensors["Codifier"]))
            else:
                p={}
                p["Codifier"]=sensors["Codifier"]
                a.append(p)
    else:
        if (r.hexists(codifier, "Codifier")):
            a.append(r.hgetall(codifier))
        else:
            if (channel.getSensor(codifier) == None):
                return "Please provide a valid Sensor Codifier"
            p={}
            p["Codifier"]=codifier
            a.append(p)
    return (Response(response=json.dumps(a),
            status=200, mimetype="application/json"))

@app.route('/sensorinfo/<codifier>')
def sensorinfo(codifier):
    return render_template('sensorinfo.html',
            sensor=channel.getSensor(codifier),
            redis=r.hgetall(codifier),
            sensordetail=json.dumps(channel.getSensor(codifier)))

@app.route('/sensormsg/<codifier>/<flag>')
def sensormsg(codifier, flag):
    p={}
    t=jph.timeNow()
    if ( codifier == MyCodifier ):
        codifier = "@@"
    p["Codifier"]=codifier
    p["Flag"]=flag
    p["Timestamp"]=t
    channel.sendCtrl(to=codifier, flag=flag, timeComponent=t)
    return (Response(response=json.dumps(p),
            status=200, mimetype="application/json"))

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
