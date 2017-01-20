from flask import Flask, url_for, render_template, Response, jsonify, request, redirect, flash
from flask_redis import FlaskRedis
import flask_login as login
from flask_sqlalchemy import SQLAlchemy
import urllib2
import json
import sys
import time
import struct
import jph
import os
import bcrypt

#
# Configure Flask & Redis
#
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'redis'
r=FlaskRedis(app)     

#
# Configure the JPH app
#
configURL="file:static/config.json"
MyCodifier="CF"
channel=jph.jph(configURL=configURL, Codifier=MyCodifier)

#
# Configure the database
#
dbname=channel.getMySensorElement("SQL")["Database"]
dbuser=channel.getMySensorElement("SQL")["User"]
dbpass=channel.getMySensorElement("SQL")["Password"]
dbhost=channel.getMySensorElement("SQL")["Host"]

try:
    f = open(os.path.expanduser(dbpass))
    sqlpassword=f.read().strip()
    f.close
except Exception as e:
    channel.logger.critical("Unexpected error reading password file: %s", e)
    sys.exit()

# SQLALCHEMY_DATABASE_URI = ("postgresql://%s:%s@%s:5432/%s" % (dbuser,sqlpassword,dbhost,dbname))
app.config['SQLALCHEMY_DATABASE_URI'] = ("postgresql://%s:%s@%s:5432/%s" % (dbuser,sqlpassword,dbhost,dbname))
if (os.getenv("JPH_DEBUG", "0")=="1"):
    app.config['SQLALCHEMY_ECHO'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    email = db.Column(db.String(120), primary_key=True)
    password = db.Column(db.String(120))

    # def __init__(self):
    #     self.email=email
    #     self.password=password
    #     self.authenticated=False

    # Flask-Login integration
    def is_authenticated(self):
        return self.authenticated

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.email

    # Required for administrative interface
    def __unicode__(self):
        return self.username

# Initialize flask-login
login_manager = login.LoginManager()
login_manager.init_app(app)

# Create user loader function
@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(user_id)

@app.route('/login',methods=['GET','POST'])
def userauthentication():
    if request.method == 'GET':
        return render_template('login.html')

    print("Login request received for: ", request.form["email"])
    dbuser=db.session.query(User).filter_by(email=request.form["email"]).first()
    if dbuser:
        pw=str(request.form["password"].encode('utf-8'))
        if bcrypt.checkpw(pw, str(dbuser.password)):
            dbuser.authenticated = True
            login.login_user(dbuser, remember = True)
            return redirect(url_for('index'))
    flash("Invalid login")
    return redirect(url_for('userauthentication'))

@app.route("/logout", methods=['GET'])
@login.login_required
def logout():
    user = login.current_user
    user.authenticated = False
    login.logout_user()
    return redirect(url_for('userauthentication'))

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
    p={}
    if (login.current_user.is_authenticated == False):
        p["message"]="Only available for logged in users"
        p["status"]="error"
        print(p)
    else:
        codifier=codifier[:2]
        flag=flag[:1]
        if (channel.getSensor(codifier) == None):
            p["message"]="Please provide a valid Codifier"
            p["status"]="warning"
        else:
            t=jph.timeNow()
            if ( codifier == MyCodifier ):
                codifier = "@@"
            p["Codifier"]=codifier
            p["Flag"]=flag
            p["Timestamp"]=t
            p["status"]="success"
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
        results = db.engine.execute(query)
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
    app.run(debug=True, use_reloader=False, host='0.0.0.0')
