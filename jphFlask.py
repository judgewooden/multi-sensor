from flask import Flask, url_for, render_template, Response, jsonify
print ("hello1")
from flask_redis import FlaskRedis
print ("hello2")
try:
    from sqlalchemy import *
    sqlokay=True
except:
    sqlokay=False
print ("hello3")

import urllib2
print ("hello4")
import json
print ("hello5")
import sys
print ("hello6")
import time
print ("hello7")
import struct
print ("hello8")
# import random
import jph
print ("hello9")
import os
print ("hello10")
# import psycopg2

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

r=FlaskRedis(app) 

#
# Configure the JPH app
#
configURL="file:static/config.json"
MyCodifier="CF"
channel=jph.jph(configURL=configURL, Codifier=MyCodifier)

if sqlokay:
    dbname=channel.getMySensorElement("SQL")["Database"]
    dbuser=channel.getMySensorElement("SQL")["User"]
    dbpass=channel.getMySensorElement("SQL")["Password"]
    dbhost=channel.getMySensorElement("SQL")["Host"]

    try:
        f = open(os.path.expanduser(dbpass))
        sqlpassword=f.read().strip()
        f.close
    except Exception as e:
        channel.logger.critical("Unexpected error reading passwording: %s", e)
        sys.exit()

    SQLALCHEMY_DATABASE_URI = ("postgresql://%s:%s@%s:5432/%s" % (dbuser,sqlpassword,dbhost,dbname))
    db = create_engine(SQLALCHEMY_DATABASE_URI)
else:
    print ("SQL IS NOT ACTIVE")
    db = ""

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', sensors = channel.getAllSensors())

@app.route('/diagram')
def diagram():
    return render_template('diagram.html', sensors = channel.getAllSensors())

@app.route('/devel')
def sensors():
    return render_template('graphdevel.html', sensors = channel.getAllSensors())

@app.route('/')
def index():
    return render_template('index.html', sensors = channel.getAllSensors())

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
        codifier=codifier[:2]
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

@app.route('/dashtable')
def dashtable():
    a=[]
    for c in channel.getAllSensors():
        p=c.copy()
        if (r.hexists(c["Codifier"], "Codifier")):
            p.update(r.hgetall(c["Codifier"]))
        a.append(p)
    return render_template('dashtable.html', sensors = a)

@app.route('/sensorinfo/<codifier>')
def sensorinfo(codifier):
    codifier=codifier[:2]
    if (channel.getSensor(codifier) == None):
        return "Please provide a valid Codifier"
    return render_template('sensorinfo.html',
            sensor=channel.getSensor(codifier),
            redis=r.hgetall(codifier),
            sensordetail=json.dumps(channel.getSensor(codifier)))

@app.route('/sensormsg/<codifier>/<flag>')
def sensormsg(codifier, flag):
    codifier=codifier[:2]
    flag=flag[:1]
    if (channel.getSensor(codifier) == None):
        return "Please provide a valid Codifier"
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

@app.route('/sensorts/<query>')
def sensorts(query):
    if not sqlokay:
        return "SQL not initialized"

    try:
        jquery=json.loads(query)
    except:
        return "Invalid JSON"

    query=""
    for r in jquery:
        try:
            c=str((r["codifier"]))[0:2]
            if (channel.getSensor(c) == None):
                return "Please provide a valid codifier"
            k=int((r["key"]))
            t=int((r["time"]))
        except:
            return "Invalid JSON"

        if k > 0:
            query= query + " UNION "
        query = query + "SELECT " + str(k) + ","
        query = query + " Timestamp AS timestamp, Value as value"
        query = query + " FROM sensor_" + c
        query = query + " WHERE Timestamp > " + str(t)
    if query=="":
        return "No rows in request"

    query=query + " ORDER BY Timestamp"

    p=[]
    try:
        results = db.engine.execute(text(query))
    except:
        return "Unknown Error with DB engine"
    # answer=results.fetchall()
    # print(answer)
    # return (Response(response=answer,
    #          status=200, mimetype="binary/octet-stream"))
    # return Flask.make_response(answer, 200, {
    #                                    'Content-type': 'binary/octet-stream',
    #                                    'Content-length': len(answer),
    #                                    'Content-transfer-encoding': 'binary'
    #                                    })
    # return (Response(response=results,
    #         status=200, mimetype="binary/octet-stream"))
    for r in results:
        row = {
            '0' : r[0],
            't' : r[1],
            'v' : r[2]
        }
        p.append(row)
    return (Response(response=json.dumps(p), status=200, mimetype="application/json"))

if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
