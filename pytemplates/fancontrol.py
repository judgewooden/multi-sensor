# mad=A4
# Aqua=A5 
n=jph.timeNow()

#
# check if we have an existing duty cycle in the network  (ie. existing value for the FAN)
#
fk=100 # assume ON and 100% MAX
times = [{{ FK|DTimestamp }}]
l=min(times)
if (l!=None):
    if(n-l < 60000):
        fk={{ FK }}

#
# check if we have a target temperature
#
target={{ FJ }}
if (target==None):
    target=37 # assume a consant if no user value


dc=100
times = [{{ A4|DTimestamp }}, {{ A5|DTimestamp }}]
l=min(times)
if (l!=None):
    if(n-l < 60000):
        maxtemp = max( [{{ A4 }}, {{ A5 }} ])
        terror = maxtemp - 37
        dc=fk + 1/6 * 5 * terror
        print(maxtemp, terror, dc, {{ FK }}, {{ A4 }}, {{ A5 }})
channel.sendData(data=dc, Codifier="FM")
channel.sendCtrl(to="FK", flag="A", timeComponent=dc)
