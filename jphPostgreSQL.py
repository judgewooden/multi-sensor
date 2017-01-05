#!/usr/bin/env python
from __future__ import print_function, absolute_import, division, nested_scopes, generators, unicode_literals
import sys
import getopt
import struct
import jph
import os
import psycopg2
import time

# -------------
# Globals
# -------------
configURL="file:static/config.json"
Codifier="Q1"

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
            Codifier=arg
except Exception as e:
    print("Error: %s" % e)
    usage()
    sys.exit()

#
# by making a Sensor a class you can store local variables
# and make a function to check the sensor every x seconds but only update the 
# data if the sensor changed within a specific tollerance
# 
# Also allow for enhanced inequiry capabilities using a peer-to-peer future prototcol
#
class postgreSQLHandler(object):

    def __init__(self):
        self.Counter=0
        self.q=None
        self.DataType={}

    def publish(self, Timestamp):
        channel.sendData(self.Counter)
        self.Counter=0

    def initdb(self):

        for s in channel.getAllSensors():
            if "DataType" in s:
                self.DataType[s["Codifier"]]=s["DataType"]
            else:
                self.DataType[s["Codifier"]]="float"

        # try:
        qs=("dbname=%s user=%s password=%s host=%s " % (dbname, dbuser, sqlpassword, dbhost))
        self.q=psycopg2.connect(qs)
        # except psycopg2.OperationalError as e:
        #     logging.critical("Unable to connect: %s", format(e))
        #     sys.exit()
        # except Exception as e:
        #     logging.critical("Unexepected error: %s", e)
        #     sys.exit()

    def updateData(self, chnl, flag, source, to, timestamp, sequence, length, sender, data, isActive):
        if self.q==None:
            self.initdb()

        if (flag == 'n'):
            channel.logger.debug("%d %s%s %s Reset=%d (SKIPPED)", timestamp, chnl, flag, source, sequence)
        else:
            cursor = self.q.cursor()
            if self.DataType[source] == "bool":
                if data:
                    data="TRUE"
                else:
                    data="FALSE"
                ans=("INSERT INTO sensor_%s VALUES (%d, %s)" % (source, timestamp, data))
            else:
                ans=("INSERT INTO sensor_%s VALUES (%d, %s)" % (source, timestamp, data))
            channel.logger.debug(ans)
            cursor.execute(ans)
            self.q.commit()
            self.Counter+=1
            # channel.logger.debug("%d %s%s %s Data=%s", timestamp, chnl, flag, source, data)

if __name__ == '__main__':
 
    channel=jph.jph(configURL=configURL, Codifier=Codifier)
    handler=postgreSQLHandler()

    dbname=channel.getMySensorElement("SQL")["Database"]
    dbuser=channel.getMySensorElement("SQL")["User"]
    dbpass=channel.getMySensorElement("SQL")["Password"]
    dbhost=channel.getMySensorElement("SQL")["Host"]

    try:
        f = open(os.path.expanduser(dbpass))
        sqlpassword=f.read().strip()
        f.close
    except Exception as e:
        logger.critical("Unexpected error reading passwording: %s", e)
        sys.exit()

    channel.logger.debug("Startup PostgreSQL")
    channel.run(dataCallback=handler.updateData, timeCallback=handler.publish)
