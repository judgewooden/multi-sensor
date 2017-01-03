#!/usr/bin/env python
from __future__ import print_function, absolute_import, division, nested_scopes, generators, unicode_literals
import sys
import getopt
import struct
import jph

#------------------------------------------------------------------
# Designed to view multicast channels and send custom Ctrl messages
#------------------------------------------------------------------

# -------------
# Globals
# -------------
comFrom=""
comTo=""
comAll=""
comFlag=""
comTarget=""
comExit=""
comChnl=""
configURL="file:static/config.json"
Codifier=""
comForce=""

# -------------
# Read Startup Parameters
# -------------
def usage():
    print("Usage: -u <url>", __file__)
    print("\t-u <url> : load the JSON configuration from a url")
    print("\t-c <code>: The Codifier of this program") 
    print("")
    print("\t-t <code>: Send a message to this Codifier (requires -f)")
    print("\t-f <flag>: Send this flag to Codifier in message (requires -t)")
    print("\t-x       : Exit after message (skip view messages on console")
    print("")
    print("\t-l <code>: Filter and show all message TO&FROM this Codifier") 
    print("\t           OR")
    print("\t-o <code>: Filter and show only message TO this Codifier") 
    print("\t-r <code>: Filter and show only messages FROM Codifier") 
    print("")
    print("\t-n <chnl>: Filter and show only this Channel (Data/Ctrl)")
    print("")
    print("\t-F       : Force ME as ON and Active to receive messages")

try:
    opts, args = getopt.getopt(sys.argv[1:], "hu:c:t:f:xl:o:r:n:F", ["force", "help", "url=", "code=", "msg-to=", "msg-flag=", "exit", "filter-from=", "filter-to=", "filter-all=", "filter-chnl="])
    for opt, arg in opts:
        if opt in ("-h", "help"):
            raise
        elif opt in ("-u", "--url"):
            configURL=arg
        elif opt in ("-c", "--code"):
            Codifier=arg[:2]
        elif opt in ("-t", "--msg-to"):
            comTarget=arg[:2]
        elif opt in ("-f", "--msg-flag"):
            comFlag=arg[:1]
        elif opt in ("-x", "--exit"):
            comExit=True
        elif opt in ("-l", "--filter-all"):
            comAll=arg[:2]
        elif opt in ("-r", "--filter-from"):
            comFrom=arg[:2]
        elif opt in ("-o", "--filter-to"):
            comTo=arg[:2]
        elif opt in ("-n", "--filter-chnl"):
            comChnl=arg[:1].upper()
        elif opt in ("-F", "--force"):
            comForce=True
    if (comTarget!="" and comFlag=="") or (comTarget=="" and comFlag!=""):
        raise ValueError("Option -t & -f are combined")
except Exception as e:
    print("Error: %s" % e)
    usage()
    sys.exit()

class ControlHandler(object):

    def __init__(self):
        self.Counter=0

    def publish(self, Timestamp):
        channel.sendData(self.Counter)
        self.Counter=0

    def theOutput(self, chnl, flag, source, to, timestamp, sequence, length, sender, data, isActive):
        self.Counter+=1

        comA = True if comAll in (source, to, "") else False
        if (comFrom!=""):
            comA = True if comFrom == source else False
        if (comTo!=""):
            comA = True if comTo == to else False

        comC = True if comChnl in (chnl[:1], "") else False

        if comA and comC:
            print("%d %s%s %s-%s %d (len=%d) (active=%s) %s" % (timestamp, chnl, flag, source, to, sequence, length, isActive, data ), sender)

if __name__ == '__main__':

    channel=jph.jph(configURL=configURL, Codifier=Codifier)
    handler=ControlHandler()
    if comTarget!="":
        channel.sendCtrl(to=comTarget, flag=comFlag)
    if comExit:
        sys.exit()
    if comForce:
        channel.sendCtrl(to=Codifier, flag='S')

    channel.run(ctrlCallback=handler.theOutput, timeCallback=handler.publish, dataCallback=handler.theOutput)
