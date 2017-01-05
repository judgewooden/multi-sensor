#!/usr/bin/env python
from __future__ import print_function, absolute_import, division, nested_scopes, generators, unicode_literals
import sys
import getopt
import struct
import jph
import os
import redis

# -------------
# Globals
# -------------
configURL="file:static/config.json"
Codifier="Q1"
comTarget=""

# -------------
# Read Startup Parameters
# -------------
def usage():
    print("Usage: -u <url>", __file__)
    print("\t-u <url> : load the JSON configuration from a url")
    print("\t-c <code>: The Sensor that this program needs to manage") 
    print("\t         :  & holds the db configurations")
    print("\t-l <code>: Create only database elements for this code")
try:
    opts, args = getopt.getopt(sys.argv[1:], "hu:c:l:", ["help", "url=", "code=", "sqlto="])
    for opt, arg in opts:
        if opt in ("-h", "help"):
            raise
        elif opt in ("-u", "--url"):
            configURL=arg
        elif opt in ("-c", "--code"):
            Codifier=arg
        elif opt in ("-l", "--sqlto"):
            comTarget=arg[:2]
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

# main 
channel=jph.jph(configURL=configURL, Codifier=Codifier)

dbname=channel.getMySensorElement("SQL")["Database"]
dbuser=channel.getMySensorElement("SQL")["User"]
dbpass=channel.getMySensorElement("SQL")["Password"]
dbhost=channel.getMySensorElement("SQL")["Host"]

f = open(os.path.expanduser(dbpass))
sqlpassword=f.read().strip()
f.close

if comTarget=="":
    print("DROP DATABASE IF EXISTS %s;" % (dbname))
    print("CREATE USER %s WITH PASSWORD '%s';" % (dbuser, sqlpassword))
    print("CREATE DATABASE %s OWNER %s;" % (dbname, dbuser) )

if comTarget=="":
    for sensor in channel.getAllSensors():
       sqltable(sensor)
else:
    sqltable(channel.getSensor(comTarget))

