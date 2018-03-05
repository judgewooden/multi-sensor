n=jph.timeNow()
timeout=60000
fn=999          # if current temp is broken, set fan to fk value
fi=True         # Fan is on by defaukt
fq=True         # Assume fan is operating
fk=100          # Assume 100% duty cycle for fan
dc=fk           # Set the duty cycle to the max 

# --- GET THESE VALUES FROM THE CONFIG !!!!
fj=35           # Assume 35 if the user do not provide a value
fg=5            # Assume 5% range if the user do not provide a value
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

    # Get the user input value for Range system
    times = [{{ FG|DTimestamp }}]
    l=min(times)
    if (l!=None):
        if(n-l < timeout):
            fg={{ FG }}

    # Is the system ON or OFF by the User
    times = [{{ FI|DTimestamp }}]
    l=min(times)
    if (l!=None):
        if(n-l < timeout):
            if (int(float("0{{ FI }}"))==1):
                fi=True
            else:
                fi=False

    # Determine our operating state
    if (fi == True):
        times = [{{ FQ|DTimestamp }}]
        l=min(times)
        if (l!=None):
            if(n-l < timeout):
                if (int(float("0{{ FI }}"))==0):
                    fq=False

        if (fn==999):
            fq=True
            channel.sendData(data="1", Codifier="FQ")
            dc = fk  # if I don't know the current temp put the fan on max
        else:
            x=(fn * fg/ 100.0)
            fnMax=fj+x
            fnMin=fj-x


            if (fq == True):
                if (fn < fnMin):
                    fq = False

            else:
                if (fn > fnMax):
                    fq = True

            if (fq == True):
                times = [{{ FK|DTimestamp }}]
                l=min(times)
                if (l!=None):
                    if(n-l < timeout):
                        fk = {{ FK }}

                terror = fnMin - fj
                dc = fk + 1/6 * 5 * terror

            print(fj, fnMax, fnMin, fn, terror)


    else:
        fq=False

    if (fq == False):
        channel.sendData(data=0, Codifier="FM")
        channel.sendCtrl(to="FK", flag="A", timeComponent=0)
        channel.sendData(data="0", Codifier="FQ")
    else:
        channel.sendData(data=dc, Codifier="FM")
        channel.sendCtrl(to="FK", flag="A", timeComponent=dc)
        channel.sendData(data="1", Codifier="FQ")

    # ----------------------------------------
    # Dew temp calculator
    # ----------------------------------------

    times = [{{ FH|DTimestamp }}]
    l=min(times)
    if (l!=None):
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
            dew = 243.04 * ( log( n3 / 100 ) + (( 17.625 * n2 ) / ( 243.04 + n2 ))) / ( 17.625 - log( n3 / 100) - (( 17.625 * n2 ) / ( 243.04 + n2 )))
            channel.sendData(data=dew, Codifier="FO")

            low = 243.04 * ((( 17.625 * dew ) / ( 243.04 + dew )) - log( fh / 100 )) / ( 17.625 + log( fh / 100) - (( 17.625 * dew ) / ( 243.04 + dew )))
            channel.sendData(data=low, Codifier="FP")
