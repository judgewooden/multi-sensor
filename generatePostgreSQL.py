#!/usr/bin/env python
from __future__ import print_function, absolute_import, division, nested_scopes, generators, unicode_literals
from getpass import getpass
import sys
import getopt
import jph
import os
import bcrypt
import hashlib
import base64

# -------------
# Globals
# -------------
configURL="file:static/config.json"
Codifier="Q1"
comTarget=""
comDB=False
comUser=False
comDrop=False

# -------------
# Read Startup Parameters
# -------------
def usage():
    print("Usage: -u <url>", __file__)
    print("\t-u <url> : load the JSON configuration from a url")
    print("\t-c <code>: The Codifier where the SQL parameters are stored")
    print("\t-l <code>: Create only table this Codifier")
    print("\t-d       : Add the database & user table creation ")
    print("\t-f       : Force the database DROP")
    print("\t-p <u:p> : Add a user:password to the database")
try:
    opts, args = getopt.getopt(sys.argv[1:], "hu:c:l:p:df", ["help", "url=", "code=", "sqlto=", "database", "user=", "force"])
    for opt, arg in opts:
        if opt in ("-h", "help"):
            raise
        elif opt in ("-u", "--url"):
            configURL=arg
        elif opt in ("-c", "--code"):
            Codifier=arg
        elif opt in ("-l", "--sqlto"):
            comTarget=arg[:2]
        elif opt in ("-d", "--database"):
            comDB=True
        elif opt in ("-f", "--force"):
            comDrop=True
        elif opt in ("-p", "--user"):
            comUser=True
            s=arg.find(":")
            if (s<1):
                raise Exception("option expects 'user:password' but colon ommited")
            u=arg[:s].strip()
            p=arg[s+1:].strip()
except Exception as e:
    print("Error: %s" % e)
    usage()
    sys.exit()

def sqltable(s):
    print("\c %s;" % dbname)
    print("CREATE TABLE Sensor_%s (" % (s["Codifier"]) )
    print("Timestamp bigint PRIMARY KEY,")
    if "DataType" in s:
        print("Value %s NOT NULL" % s["DataType"])
    else:
        print("Value float NOT NULL")
    print(");")
    print("GRANT ALL PRIVILEGES ON TABLE Sensor_%s to %s;" % (s["Codifier"], dbuser))

def createDB():
    if comDrop:
        print("DROP DATABASE IF EXISTS %s;" % (dbname))
    print("CREATE USER %s WITH PASSWORD '%s';" % (dbuser, sqlpassword))
    print("CREATE DATABASE %s OWNER %s;" % (dbname, dbuser) )
    print("\c %s;" % dbname)
    print("CREATE TABLE Users (")
    print("email varchar(120) PRIMARY KEY,")
    print("password varchar(120)")
    print(");")
    print("GRANT ALL PRIVILEGES ON TABLE Users to %s;" % (dbuser))

# main 
channel=jph.jph(configURL=configURL, Codifier=Codifier)

dbname=channel.getMySensorElement("SQL")["Database"]
dbuser=channel.getMySensorElement("SQL")["User"]
dbpass=channel.getMySensorElement("SQL")["Password"]
dbhost=channel.getMySensorElement("SQL")["Host"]

f = open(os.path.expanduser(dbpass))
sqlpassword=f.read().strip()
f.close

if comDB:
    createDB()
    for sensor in channel.getAllSensors():
       sqltable(sensor)

if comTarget!="":
    sqltable(channel.getSensor(comTarget))

if comUser:
    p_encode=p.encode('utf-8')
    p_hashed = bcrypt.hashpw(p_encode, bcrypt.gensalt())
    print("\c %s;" % dbname)
    print("INSERT INTO Users VALUES ('%s', '%s');" % (u, p_hashed))
