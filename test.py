
var=" a b c d@{{ C3|Redis|DPacketsLost }}+x {}, b {{ y|iot }}---\
-\
123\
 xx"

def jphlookup(var):
    s=var.find("|")
    if s > 0:
        field=var[s+1:]
        var=var[:s]
        print(var,field)
        s=field.find("|")
        if s > 0:
            cache=field[:s]
            field=field[s+1:]
        else:
            cache="Redis"
    else:
        cache="Redis"
        field="Value"
    var=var.strip()
    cache=cache.strip()
    field=field.strip()
    print(var, cache, field)
    if var == 'x':
        return str(12)
    if var == 'y':
        return "OMG THIS WORKS"
    return ""

def jphme(var):
    new=""
    s=var.find("{{")
    if s > 0:
        e=var.find("}}", s)
        if e > 0:
            return var[:s] + jphlookup(var[s+2:e]) + jphme(var[e+2:])
        return var
    return var

x=jphme(var)
print(x)
# print(x.jphme)                    flow1 = {{ X1 }}\
                #     temp1 = {{ A7 }}\
                #     flow2 = {{ Y1 }}\
                #     temp2 = {{ A2 }}\
                #     return ((flow1 * temp1 + flow2 * temp2)/(flow1 + flow2))",
                # "Proxy":[{
