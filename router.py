#!/usr/bin/env python
from __future__ import print_function, absolute_import, division, nested_scopes, generators, unicode_literals
import socket
import struct
import select

def openSocket(addr, port, interface):
    tAddr = socket.getaddrinfo(addr, None)[0]
    tsocket = socket.socket(tAddr[0], socket.SOCK_DGRAM)
    tsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tsocket.bind(('', port))
    # group_bin = socket.inet_pton(tAddr[0], tAddr[4][0])
    # mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
    # tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(addr) + socket.inet_aton(interface))
    # tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface))
    tsocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
    return tsocket

# Configure here the network card binding and the multicast address
northCtrl=openSocket("227.0.0.111", 8001, "192.168.0.225")
northData=openSocket("227.0.0.112", 8002, "192.168.0.225")

southCtrl=openSocket("226.0.0.221", 7001, "192.168.136.4")
southData=openSocket("226.0.0.222", 7002, "192.168.136.4")

inputs = [northCtrl, southCtrl, northData, southData]
forever=True
while forever:
    readable, writable, exceptional = select.select(inputs, [], [])
    for s in readable:
        if s == southCtrl:
            # so="Ctrl-South"
            # print(so, sender)
            data, sender = southCtrl.recvfrom(1500)
            northCtrl.sendto(data, ("227.0.0.111", 8001))
        if s == northCtrl:
            # so="Ctrl-North"
            # print(so, sender)
            data, sender = northCtrl.recvfrom(1500)
            southCtrl.sendto(data, ("226.0.0.221", 7001))
        if s == southData:
            # so="Data-South"
            # print(so, sender)
            data, sender = southData.recvfrom(1500)
            northData.sendto(data, ("227.0.0.112", 8002))
        if s == northData:
            # so="Data-North"
            # print(so, sender)
            data, sender = northData.recvfrom(1500)
            southData.sendto(data, ("226.0.0.222", 7002))
            
