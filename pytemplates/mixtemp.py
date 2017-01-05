#
# 
# This will be called after all modules are loaded (see sensors.py)
# channel (jph) will be establised
# 
# {{ }} syntax is:  Codifier | location | Field
#  where location is either 'redis' or 'config'
#           ('redis' is default if ommitted)
#           ('Value' is default if Field ommitted)
#
#

times = [{{ C3|DTimestamp }}, {{ A2|DTimestamp }}, {{ Y1|DTimestamp }}, {{ X1|DTimestamp }}]
l=min(times)
if (l!=None):
    n=jph.timeNow()
    if (n-l < 20000):
        temp1 = {{ C3 }}
        temp2 = {{ A2 }}
        flow1 = {{ Y1 }}
        flow2 = {{ X1 }}
        try:
            a=((flow1 * temp1 + flow2 * temp2)/(flow1 + flow2))
        except Exception as e:
            channel.logger.warning("Unexpected result: %s", e)
            raise
        else:
            channel.sendData(data=a, Codifier="PB")
