#
# This will be called to perform a calculation 
# - channel (jph) will be establised
# - a pre-processor will fill in the variables betweek double curly brackets {{ }}
# - The syntax of a variable is:  {{ Codifier | Location | Field }}
#    where Location is either 'redis' or 'config'
#    defaults are ('redis' if Location is ommitted)
#                 ('Value' if Field is ommitted)
#
# - examples:
#      {{ C4 }} will return the Value from Redis it is the same as:
#      {{ C4|Value }} or {{ C4|redis|Value }}
#
#      {{ C4|config|Symbol }} will return the field Symbol from the configuration
#      {{ C4|TDuration }} will return the delay from the last ping message
#

#
# This function calculates the mixtemp and send the result to Codifier="PB"
# - the calculation is only performed if an update for all variables have been receveived
#   in the last 20 seconds (20000 ms)
# - the calculation is a in try: loop to demonstrate that you can write message 
#   to a log file using channel.logger
# - the result is send to the network using channel.sendData
#
n=jph.timeNow()

times = [{{ A4|DTimestamp }}, {{ A5|DTimestamp }}, {{ Y2|DTimestamp }}, {{ X2|DTimestamp }}]
l=min(times)
if (l!=None):
    if (n-l < 20000):
        temp1 = {{ A4 }}
        flow1 = {{ X2 }}
        flow2 = {{ Y2 }}
        temp2 = {{ A5 }}
        try:
            a=((flow1 * temp1 + flow2 * temp2)/(flow1 + flow2))
        except Exception as e:
            channel.logger.warning("Unexpected result: %s", e)
            raise
        else:
            channel.sendData(data=a, Codifier="PB")

#
# This function calculates the delta temp 
#
times = [{{ A4|DTimestamp }}, {{ A3|DTimestamp }}]
l=min(times)
if (l!=None):
    if (n-l < 20000):
        dt={{ A4 }} - {{ A3 }}
        channel.sendData(data=dt, Codifier="PC")

        times = [{{ X2|DTimestamp }}]
        l=min(times)
        if (l!=None):
            if (n-l < 20000):
                wm=dt * 65.851 * {{ X2 }}
                channel.sendData(data=wm, Codifier="PF")
         

times = [{{ A5|DTimestamp }}, {{ A3|DTimestamp }}]
l=min(times)
if (l!=None):
    if (n-l < 20000):
        dt={{ A5 }} - {{ A3 }}
        channel.sendData(data=dt, Codifier="PD")

        times = [{{ Y2|DTimestamp }}]
        l=min(times)
        if (l!=None):
            if (n-l < 20000):
                wa=dt * 65.851 * {{ Y2 }}
                channel.sendData(data=wa, Codifier="PE")
 
times = [{{ W1|DTimestamp }}, {{ W4|DTimestamp }}]
l=min(times)
if (l!=None):
    if (n-l < 20000):
        cp={{ W4 }} - {{ W1 }}
        channel.sendData(data=cp, Codifier="PG")

times = [{{ W7|DTimestamp }}, {{ W1|DTimestamp }}]
l=min(times)
if (l!=None):
    if (n-l < 20000):
        cm={{ W7 }} - {{ W4 }}
        channel.sendData(data=cm, Codifier="PH")

times = [{{ A1|DTimestamp }}, {{ A2|DTimestamp }}]
l=min(times)
if (l!=None):
    if (n-l < 20000):
        dt={{ A1 }} - {{ A2 }}
        channel.sendData(data=dt, Codifier="PI")

        times = [{{ X2|DTimestamp }}, {{ Y2|DTimestamp }}]
        l=min(times)
        if (l!=None):
            if (n-l < 20000):
                tf={{ X2 }} + {{ Y2 }}
                wa=dt * 65.851 * tf
                channel.sendData(data=wa, Codifier="PK")

times = [{{ X2|DTimestamp }}, {{ Y2|DTimestamp }}]
l=min(times)
if (l!=None):
    if (n-l < 20000):
        tf={{ X2 }} + {{ Y2 }}
        channel.sendData(data=tf, Codifier="PJ")

times = [{{ M2|DTimestamp }}, {{ M4|DTimestamp }}]
l=min(times)
xs=False
if (l!=None):
    if (n-l < 840000):
        tf={{ M2 }} + {{ M4 }}
        channel.sendData(data=tf, Codifier="PL")
        xs=True
if (xs==False):
    m2={{ M2|DTimestamp }}
    if (m2!=None):
        if (n-m2 < 840000):
            tf={{ M2 }}
            channel.sendData(data=tf, Codifier="PL")
    m4={{ M4|DTimestamp }}
    if (m4!=None):
        if (n-m4 < 840000):
            tf={{ M4 }}
            channel.sendData(data=tf, Codifier="PL")

# mad=A4
# Aqua=A5 

dc=100
times = [{{ A4|DTimestamp }}, {{ A5|DTimestamp }}]
l=min(times)
if (l!=None):
    if(n-l < 60000):
        maxtemp = max( [{{ A4 }}, {{ A5 }} ])
        terror = maxtemp - 37
        dc={{ FK }} + 1/6 * 5 * terror
        print(maxtemp, terror, dc, {{ FK }}, {{ A4 }}, {{ A5 }})
channel.sendCtrl(to="FK", flag="A", timeComponent=dc)


