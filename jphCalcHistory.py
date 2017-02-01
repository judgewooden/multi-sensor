#!/usr/bin/env python
from __future__ import print_function, absolute_import, division, nested_scopes, generators, unicode_literals
import sys
import getopt
import struct
import jph
import os
import psycopg2
import time
import calendar
import statistics

# -------------
# Globals
# -------------
configURL="file:static/config.json"
Codifier=""

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

class postgresCalcHandler(object):

    def __init__(self):
        self.Counter=0
        self.db=None
        self.MaxTimeProcessed={}
        self.LastTime=0

    def publish(self, Timestamp, command="", number=None):
        if self.LastTime!=0:   # Skip the first time to build up an average
            t=jph.timeNow()
            a=self.Counter*(60/((t-self.LastTime)/1000))
            channel.sendData(int(a))
        self.LastTime=jph.timeNow()
        self.Counter=0

        if self.db==None:
            self.initdb()

        cur=self.db.cursor()
        for tgap in ["10min", "hour"]:
            for s in channel.getAllSensors():
                if "DataType" in s:
                    if s["DataType"] == 'bool':
                        continue

                l=self.MaxTimeProcessed[s["Codifier"]+tgap]
                while True:
                    if tgap=="hour":
                        n=l+3600000
                    else:
                        n=l+600000

                    t=jph.timeNow()
                    if n>t:
                        break

                    q=("SELECT Value FROM sensor_%s WHERE Timestamp>%s and Timestamp<=%s" % (s["Codifier"], l, n))
                    channel.logger.debug(q)
                    channel.logger.debug("Timestamp > %s", time.gmtime(l/1000))
                    channel.logger.debug("Timestamp <= %s", time.gmtime(n/1000))
                    cur.execute(q)
                    a=cur.fetchall()

                    channel.logger.debug("return len: %s", len(a))
                    if len(a)>0:
                        d=[]
                        for r in a:
                            (v,)=(r[0],)
                            d.append(v)
                        # try:
                        try:
                            mean=statistics.mean(d)
                        except:
                            mean="NULL"
                        try:
                            mode=statistics.mode(d)
                        except:
                            mode="NULL"
                        try:
                            median=statistics.median(d)
                        except:
                            median="NULL"
                        try:
                            maxi=max(d)
                        except:
                            maxi="NULL"
                        try:
                            mini=min(d)
                        except:
                            mini="NULL"
                        try:
                            stddev=statistics.pstdev(d)
                        except:
                            stddev="NULL"

                        q=("INSERT INTO sensor_%s_%s VALUES (%d, %s, %s, %s, %s, %s, %s)" % (s["Codifier"], tgap, n, mean, mode, median, maxi, mini, stddev))
                        channel.logger.debug(q)
                        cur.execute(q)
                        self.db.commit()

                        self.MaxTimeProcessed[s["Codifier"]+tgap]=n
                        self.Counter+=1
                        l=n
                    else:
                        # get the first available value and calculate from there
                        q=("SELECT Timestamp FROM sensor_%s WHERE Timestamp>%s ORDER BY Timestamp ASC LIMIT 1" % (s["Codifier"], l))
                        channel.logger.debug(q)
                        # channel.logger.debug("Timestamp > %s", time.gmtime(l/1000))
                        cur.execute(q)
                        a=cur.fetchall()
                        channel.logger.debug("return len: %s", len(a))
                        if len(a)==1:
                            for r in a:
                                (x,)=(r[0],)
                            #-- Wrap time back to the begining of the hour
                            y1=(time.gmtime(x/1000))
                            print(y1)
                            y_w=list(y1)
                            if (tgap=="hour"):
                                y_w[4]=0
                            if (tgap=="10min"):
                                y_w[4]=y_w[4]-(y_w[4]%10)
                            y_w[5]=0
                            y_w[6]=0
                            y_w[7]=0
                            y_w[8]=-1
                            print(y_w)
                            y=time.struct_time(tuple(y_w))
                            print(y)
                            l=int(calendar.timegm(y)*1000)
                            print(time.gmtime(l/1000))
                        else:
                            break
        return jph.STATE.GOOD

    def initdb(self):

        # try:
        qs=("dbname=%s user=%s password=%s host=%s " % (dbname, dbuser, sqlpassword, dbhost))
        self.db=psycopg2.connect(qs)
        cur=self.db.cursor()

        channel.logger.debug("Loading Last calculated values")
        for tgap in ["10min", "hour"]:
            for s in channel.getAllSensors():
                q=("SELECT Timestamp FROM sensor_%s_%s ORDER BY Timestamp DESC LIMIT 1" % (s["Codifier"], tgap)) 
                channel.logger.debug(q)
                cur.execute(q)
                a=cur.fetchall()

                self.MaxTimeProcessed[s["Codifier"]+tgap]=0
                if len(a)==1:
                    for r in a:
                        (self.MaxTimeProcessed[s["Codifier"]+tgap],)=(r[0],)

if __name__ == '__main__':
 
    channel=jph.jph(configURL=configURL, Codifier=Codifier)
    handler=postgresCalcHandler()

    dbname=channel.getMySensorElement("SQL")["Database"]
    dbuser=channel.getMySensorElement("SQL")["User"]
    dbpass=channel.getMySensorElement("SQL")["Password"]
    dbhost=channel.getMySensorElement("SQL")["Host"]

    try:
        f = open(os.path.expanduser(dbpass))
        sqlpassword=f.read().strip()
        f.close
    except Exception as e:
        channel.logger.critical("Unexpected error reading password: %s", e)
        sys.exit()

    channel.logger.debug("Startup CalcHistory")
    channel.run(timeCallback=handler.publish)

