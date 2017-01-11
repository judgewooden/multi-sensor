from flask import Flask, url_for, render_template, Response, jsonify
from flask_redis import FlaskRedis
from sqlalchemy import *

import urllib2
import json
import sys
import time
import struct
# import random
import jph
import os
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
# print (SQLALCHEMY_DATABASE_URI)

import pprint
db = create_engine(SQLALCHEMY_DATABASE_URI)
# db.echo = True  # We want to see the SQL we're creating
# metadata = MetaData(db)
# sensor = Table('sensor_Q1', metadata, autoload=True)

# qs=("dbname=%s user=%s password=%s host=%s " % (dbname, dbuser, sqlpassword, dbhost))
# q=psycopg2.connect(qs)
# cursor = q.cursor()
# cursor.execute("SELECT * FROM sensor_Q1")
# records = cursor.fetchall()
# pprint.pprint(records)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', sensors = channel.getAllSensors())

@app.route('/diagram')
def diagram():
    return render_template('diagram.html', sensors = channel.getAllSensors())

@app.route('/')
def sensors():
    return render_template('graphdevel.html', sensors = channel.getAllSensors())

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
