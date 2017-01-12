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
