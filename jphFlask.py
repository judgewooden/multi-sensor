from flask import Flask, url_for, render_template, Response, jsonify, request, redirect, flash, send_file
from flask_redis import FlaskRedis
import flask_login as login
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy.exc
import urllib2
import json
import sys
import time
import struct
import jph
import os
import bcrypt
import getopt
import random

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
            MyCodifier=arg
except Exception as e:
    print("Error: %s" % e)
    usage()
    sys.exit()

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

# Initialize flask-login
login_manager = login.LoginManager()
login_manager.init_app(app)

# Users login protection
class User(db.Model):
    __tablename__ = 'users'
    email = db.Column(db.String(120), primary_key=True)
    password = db.Column(db.String(120))

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
        return self.email

# users has graphs
class Graphs(db.Model):
    __tablename__ = 'graphs'
    name = db.Column(db.String(120), primary_key=True)
    email = db.Column(db.String(120), primary_key=True)
    settings = db.Column(db.Text)

    def __init__(self, name, settings):
        user = login.current_user
        self.name = name
        self.email = user.get_id()
        self.settings = settings

# Create user loader function
@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(user_id)

@login_manager.unauthorized_handler
def handle_needs_login():
    flash("You have to be logged in to access this page.")
    return redirect(url_for('userauthentication', next=request.endpoint))

@app.route('/login',methods=['GET','POST'])
def userauthentication():
    if request.method == 'GET':
        return render_template('login.html')

    dbuser=db.session.query(User).filter_by(email=request.form["email"]).first()
    if dbuser:
        pw=str(request.form["password"].encode('utf-8'))
        if bcrypt.checkpw(pw, str(dbuser.password)):
            dbuser.authenticated = True
            login.login_user(dbuser, remember = True)
            return redirect(url_for('index'))
            
    flash("Invalid login")
    return redirect(url_for('userauthentication'))

@app.route("/graphdb", methods=['POST'])
@login.login_required
def graph_db():
    p={}
    p["status"]="error"         # assume error unless 
    try:
        a=request.form["action"]
        n=request.form["name"]
        v=request.form["settings"]
    except:
        p["message"]="Not proper structured message"
    else:
        if (n==""):
            p["message"]="a Blank name is not allowed"
        else:
            if (a=='save' or a=='delete'):
                user = login.current_user
                email = user.get_id()
                graph=Graphs.query.filter_by(email=email, name=n).first()
                if graph is None:
                    p["message"]="Can not find " + n + " record."
                else:
                    try:
                        db.session.delete(graph)
                        db.session.commit()
                    except sqlalchemy.exc.IntegrityError as e:
                        p["message"]="Error: " + e.message
                    else:
                        p["message"]=n + " deleted"
                        p["status"]="success"

            if (a=='add' or a=='save'):
                graph=Graphs(name=n,settings=v)
                try:
                    db.session.add(graph)
                    db.session.commit()
                except sqlalchemy.exc.IntegrityError as e:
                    if e.message.find("already exists") > 0:
                        p["message"]="Record already exists, use update"
                    else:
                        p["message"]="Error: " + e.message
                    db.session.rollback()
                else:
                    p["message"]=n + " saved"
                    p["status"]="success"

    return (Response(response=json.dumps(p),
            status=200, mimetype="application/json"))

@app.route("/logout", methods=['GET'])
@login.login_required
def logout():
    user = login.current_user
    user.authenticated = False
    login.logout_user()
    return redirect(url_for('userauthentication'))

@app.route('/flowanalysis')
def flowanalysis():
    return render_template('flowanalysis.html')

@app.route('/wateranalysis')
def wateranalysis():
    return render_template('wateranalysis.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', sensors = channel.getAllSensors())

@app.route('/diagram')
def diagram():
    return render_template('diagram.html', sensors = channel.getAllSensors())

@app.route('/component')
def component():
    return render_template('component.html', sensors = channel.getAllSensors())

@app.route('/devel')
@login.login_required
def sensors():
    user = login.current_user
    email = user.get_id()
    allgraphs = Graphs.query.with_entities(Graphs.name, Graphs.settings).filter_by(email=email).all()

    r=[]
    for row in allgraphs:
        x={}
        (x["name"], x["settings"])=row
        r.append(x)
    
    s=[]
    for sensor in channel.getAllSensors():
        x = sensor["Codifier"]
        s.append(str(x))

    return render_template('graphdevel.html', graphs=r, sensors = channel.getAllSensors(), codifiers=s)

@app.route('/')
def index():
    return render_template('index.html', sensors = channel.getAllSensors())

def getlog(logfilter=None):
    loghist=[]
    with open('/var/log/jph.log') as f:
        f.seek (0, 2)                           # Seek @ EOF
        fsize = f.tell()                        # Get Size
        f.seek (max (fsize-(120*1000), 0), 0)   # Set position to last 1000 lines (estimated)
        for line in f:
            if logfilter==None:
                loghist.append(line)
            elif logfilter in line:
                loghist.append(line)
    return loghist

@app.route('/logview')
@app.route('/logview/<logfilter>')
def logview(logfilter=None): 
    loghist=getlog(logfilter)
    return render_template('logview.html', loghist=loghist[1:])

@app.route('/sensorlog/')
@app.route('/sensorlog/<logfilter>')
def sensorlog(logfilter=None):
    loghist=getlog(logfilter)
    return (Response(response=json.dumps(loghist[1:]),
            status=200, mimetype="application/json"))

@app.route('/sensorboard/<codifier>')
def sensorboard(codifier=None):
    codifier=codifier[:2]
    if (channel.getSensor(codifier) == None):
        return "Please provide a valid Codifier"
    return render_template('sensorboard.html',
            sensor=channel.getSensor(codifier), sensors = channel.getAllSensors())

@app.route('/ntp')
def ntp():
    x={}
    x["time"]=jph.timeNow()
    return (Response(response=json.dumps(x),
            status=200, mimetype="application/json"))


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
@app.route('/sensormsg/<codifier>/<flag>/<number>')
def sensormsg(codifier, flag, number=None):
    p={}
    p["status"]="error"                 # assume error
    if (login.current_user.is_authenticated == False):
        p["message"]="Only available for logged in users"
    else:
        try:
            codifier=codifier[:2]
            flag=flag[:1]
            if flag in "AE":
                t=float(number)
            else:
                t=jph.timeNow()
        except:
            p["message"]="Unexpected error interpreting request"
        else:
            if (channel.getSensor(codifier) == None):
                p["message"]="Please provide a valid Codifier"
            else:
                if ( codifier == MyCodifier ):
                    codifier = "@@"
                p["Codifier"]=codifier
                p["Flag"]=flag
                p["Value"]=t
                p["status"]="success"
                channel.sendCtrl(to=codifier, flag=flag, timeComponent=t)
    return (Response(response=json.dumps(p),
            status=200, mimetype="application/json"))

@app.route('/sensorts/<query>')
def sensorts(query):
    try:
        j=json.loads(query)
    except:
        return "Invalid JSON"

    q=""
    for r in j:
        try:
            c=str((r["codifier"]))[0:2]
            if channel.getSensor(c) == None:
                return "Not a valid codifier"
            k=int((r["key"]))
            y=r["field"]
            t=int((r["time"]))
            s=y.find("-")
            if(s<1):
                a=y
                b=""
            else:
                a=y[:s]
                b=y[s+1:]
            if a not in ["value", "mean", "median", "mode", "max", "min", "stdev"]:
                raise
            if b not in ["hour", "10min", ""]:
                raise
        except:
            return "Invalid JSON"

        if k > 0:
            q= q + " UNION "
        q = q + "SELECT " + str(k) + ","
        q = q + " Timestamp AS timestamp, "
        q = q + a + " AS value"
        q = q + " FROM sensor_" + c
        if b!="":
            q = q + "_" + b
        q = q + " WHERE Timestamp > " + str(t)
        q = q + " AND " + a + " IS NOT NULL"
    if q=="":
        return "No rows in request"

    q=q + " ORDER BY Timestamp"

    p=[]
    try:
        u = db.engine.execute(q)
    except:
        return "Unknown Error with DB engine"

    for r in u:
        w = {
            '0' : r[0],
            't' : r[1],
            'v' : r[2]
        }
        p.append(w)
    return (Response(response=json.dumps(p), status=200, mimetype="application/json"))

@app.errorhandler(404)
def page_not_found(e):
    flash("404 Error. Page not found.")
    rand=str(random.randint(2, 32))
    return render_template('404.html', rand=rand)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, host='0.0.0.0')
