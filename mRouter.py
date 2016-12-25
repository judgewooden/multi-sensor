import socket
import struct
import select

def openSocket(addr, port, interface):
    tAddr = socket.getaddrinfo(addr, None)[0]
    tsocket = socket.socket(tAddr[0], socket.SOCK_DGRAM)
    tsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tsocket.bind(('', port))
    group_bin = socket.inet_pton(tAddr[0], tAddr[4][0])
    mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
    tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface))
    tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
    return tsocket

north=openSocket("224.0.0.251", 8002, "192.168.0.225")
south=openSocket("224.0.0.251", 8001, "192.168.136.4")

inputs = [north, south]
forever=True
while forever:
    readable, writable, exceptional = select.select(inputs, [], [])
    for s in readable:
        if s == north:
            so="N"
            data, sender = north.recvfrom(1500)
            south.sendto(data, ("224.0.0.251", 8001))
        if s == south:
            so="S"
            data, sender = south.recvfrom(1500)
            # north.sendto(data, ("224.0.0.251", 8001))
            
        (timestamp, source, flag, length,), value = struct.unpack('I2s1sI', data[:12]), data[12:]
        print (so, sender, timestamp, source, flag)
