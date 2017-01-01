import socket
import struct
import select

def openSocket(addr, port, interface):
    tAddr = socket.getaddrinfo(addr, None)[0]
    tsocket = socket.socket(tAddr[0], socket.SOCK_DGRAM)
    tsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tsocket.bind(('', port))
    print(tAddr, port)
    # group_bin = socket.inet_pton(tAddr[0], tAddr[4][0])
    # mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
    # tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(addr) + socket.inet_aton(interface))
    # tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface))
    tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
    return tsocket

northCtrl=openSocket("227.0.0.111", 8001, "192.168.0.225")
southCtrl=openSocket("226.0.0.221", 7001, "192.168.136.4")
northData=openSocket("227.0.0.112", 8002, "192.168.0.225")
southData=openSocket("226.0.0.222", 7002, "192.168.136.4")

inputs = [northCtrl, southCtrl, northData, southData]
# inputs = [northData, northCtrl]
print(inputs)
forever=True
while forever:
    readable, writable, exceptional = select.select(inputs, [], [])
    for s in readable:
        if s == southCtrl:
            so="Ctrl-South"
            data, sender = southCtrl.recvfrom(1500)
            print(so, sender)
            northCtrl.sendto(data, ("227.0.0.111", 8001))
        if s == northCtrl:
            so="Ctrl-North"
            data, sender = northCtrl.recvfrom(1500)
            print(so, sender)
            southCtrl.sendto(data, ("226.0.0.221", 7001))
        if s == southData:
            so="Data-South"
            data, sender = southData.recvfrom(1500)
            print(so, sender)
            northData.sendto(data, ("227.0.0.112", 8002))
        if s == northData:
            so="Data-North"
            data, sender = northData.recvfrom(1500)
            print(so, sender)
            southData.sendto(data, ("226.0.0.222", 7002))
            
