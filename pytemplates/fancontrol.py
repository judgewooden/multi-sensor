# mad=A4
# Aqua=A5 

n=jph.timeNow()

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
