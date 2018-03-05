n=jph.timeNow()
timeout=60000
fn=999          # if current temp is broken, set fan to fk value
fi=False
fk=100          # Assume 100% duty cycle for fan
fj=35           # Assume 35 if the user do not provide a value
fh=80           # assume 80% humidity target if there is not user value

if ({{ FL }}!=None):

    # Calculate Current Temp
    times = [{{ A4|DTimestamp }}, {{ A5|DTimestamp }}]
    l=min(times)
    if (l!=None):
        if(n-l < timeout):
            fn = max( [{{ A4 }}, {{ A5 }} ])
            channel.sendData(data=fn, Codifier="FN")

    # Get the user input value for Target Temp
    times = [{{ FJ|DTimestamp }}]
    l=min(times)
    if (l!=None):
        if(n-l < timeout):
            fj={{ FJ }}

    # Is the system on, if so get current duty cycle
    if (int("0{{ FI }}")==1):
        fi=True
        times = [{{ FK|DTimestamp }}]
        l=min(times)
        if (l!=None):
            if(n-l < timeout):
                fk={{ FK }}
    else:
        channel.sendData(data=0, Codifier="FM")
        channel.sendCtrl(to="FK", flag="A", timeComponent=0)
        fk=0

    if (fi==True):
        if (fn==999):
            dc=fk  # if I don't know the current temp put the fan on max
        else:
            terror = fn - fj
            dc=fk + 1/6 * 5 * terror
        channel.sendData(data=dc, Codifier="FM")
        channel.sendCtrl(to="FK", flag="A", timeComponent=dc)

    # -----------------------------------------
    # Control if the Fan should be on or of
    # -----------------------------------------
    
    #  if ( int("{{ FI }}") != 1 ):
    #      channel.sendCtrl(to="FQ", flag="A", timeComponent=0)
    #  else:

    # ----------------------------------------
    # Dew temp calculator
    # ----------------------------------------

    times = [{{ FH|DTimestamp }}]
    l=min(times)
    if (l!=None)
        if(n-l < timeout):
            fh={{ FH }}

    #
    # check of the nest values are recent
    # 
    times = [ {{ N3 | DTimestamp }} ]
    l = min(times)
    if (l!=None):
        if(n-l < timeout):
            n3={{ N3 }}
            n2={{ N2 }}
            dew =243.04 * ( log( n3 / 100 ) + (( 17.625 * n2 ) / ( 243.04 + n2 ))) / ( 17.625 - log( n3 / 100) - (( 17.625 * n2  / ( 243.04 + n2 ))
            channel.sendData(data=dew, Codifier="FO")

            low =243.04 * ((( 17.625 * dew ) / ( 243.04 + dew )) - log( fh / 100 )) / ( 17.625 + log( fh / 100) - (( 17.625 * dew ) / ( 243.04 + dew )))
            channel.sendData(data=low, Codifier="FP")
