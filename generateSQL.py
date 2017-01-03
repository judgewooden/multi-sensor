#!/usr/bin/env python
#
# Read from 
import logging
import logging.config
import os
import getopt
import sys
import urllib2
import json
import random
import time
import struct
import socket
import jphconfig
print("REWRITE ALL OF THIS - IT DOES NOT SUPPROT THE NEW CONFIG YET")
sys.exit()
# -------------
# Read Startup Parameters
# -------------
def readParams(configURL, myCodifier):

    def usage():
        print("Usage: -u <url>", __file__)
        print("\t-u <url> : load the JSON configuration from a url")
        print("\t-d <db>  : <mandatory> The sensor that holds the db configurations")
        print("\t-c <code>: <optional> Generate SQL only for this sensor")

    configURL=os.getenv("JPH_CONFIG", configURL)
    myDatabase=""

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hu:c:d:", ["help", "url=", "code=", "db="])
        for opt, arg in opts:
            if opt in ("-h", "help"):
                raise
            elif opt in ("-u", "--url"):
                configURL=arg
            elif opt in ("-c", "--code"):
                myCodifier=arg
            elif opt in ("-d", "--database"):
                myDatabase=arg
        # if myCodifier == "" :
        #     raise ValueError("Option <code> is mandatory")
        if configURL == "" :
            raise ValueError("Option <url> is mandatory")
        if myDatabase == "" :
            raise ValueError("Option <db> is mandatory")
    except Exception as e:
        print("Error: %s" % e)
        usage()
        sys.exit()
    return (configURL, myCodifier, myDatabase)

#
# Build the SQL
#
def sqlsensor(dbsensor, lsensor):

    print("\c %s;" % dbsensor["Sensor"]["SQL"]["Database"])
    print("CREATE TABLE Sensor_%s (" % lsensor["Codifier"] )
    print("Timestamp timestamp PRIMARY KEY,")
    if "DataType" in lsensor:
        print("Value %s NOT NULL" % lsensor["DataType"])
    else:
        print("Value float NOT NULL")
    print(");")
    print("GRANT ALL PRIVILEGES ON TABLE Sensor_%s to %s;" % (lsensor["Codifier"], dbsensor["Sensor"]["SQL"]["User"]))
    print("")

def sqldatabase(dbsensor):

    try:
        f = open(os.path.expanduser(dbsensor["Sensor"]["SQL"]["Password"]))
        sqlpassword=f.read().strip()
        f.close
    except:
        logger.critical("Unexpected error reading %s", mySensor["Sensor"]["SQL"]["Password"])
        sys.exit()

    print("DROP DATABASE IF EXISTS %s;" % dbsensor["Sensor"]["SQL"]["Database"])
    print("CREATE USER %s WITH PASSWORD '%s';" % (dbsensor["Sensor"]["SQL"]["User"], sqlpassword))
    print("CREATE DATABASE %s OWNER %s;" % (dbsensor["Sensor"]["SQL"]["Database"], dbsensor["Sensor"]["SQL"]["User"]) )
    print("")

def main():

    for sensor in configJSON["Sensors"]:
        if sensor["Codifier"] == myDatabase:
            dbsensor=sensor

    if (myCodifier!=""):
        for sensor in configJSON["Sensors"]:
            if sensor["Codifier"] == myCodifier:
                sqlsensor(dbsensor, sensor)
    else:
        sqldatabase(dbsensor)
        for sensor in configJSON["Sensors"]:
                sqlsensor(dbsensor, sensor)

if __name__ == '__main__':

    (configURL, myCodifier, myDatabase)=readParams("file:static/jphmonitor.json", "")
    isActive=""
    (logger, configJSON, mySensor, isActive)=jphconfig.loadconfig(configURL, myDatabase, isActive)
    main()
