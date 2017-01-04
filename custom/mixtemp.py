# temp1 = {{ A7 }}
# flow2 = {{ Y1|config|TimeoutWarning }}
temp2 = {{ A2 }}
# return ((flow1 * temp1 + flow2 * temp2)/(flow1 + flow2))
channel.sendData(data=temp2, Codifier="PB")
