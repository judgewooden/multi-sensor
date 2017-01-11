#
# 
# This will be called after all modules are loaded (see sensors.py)
# channel (jph) will be establised
# 
# {{ }} syntax is:  Codifier | Location | Field
#  where Location is either 'redis' or 'config'
#           ('redis' is default if ommitted)
#           ('Value' is default if Field ommitted)
#
#

times = [{{ A4|DTimestamp }}, {{ A5|DTimestamp }}, {{ Y2|DTimestamp }}, {{ X2|DTimestamp }}]
l=min(times)
if (l!=None):
    n=jph.timeNow()
    if (n-l < 20000):
        temp1 = {{ A4 }}
        temp2 = {{ A5 }}
        flow1 = {{ Y2 }}
        flow2 = {{ X2 }}
        try:
            a=((flow1 * temp1 + flow2 * temp2)/(flow1 + flow2))
        except Exception as e:
            channel.logger.warning("Unexpected result: %s", e)
            raise
        else:
            channel.sendData(data=a, Codifier="PB")
