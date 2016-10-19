#!/usr/bin/env python
#
# Receive From multicast address

MYPORT = 8123
MYGROUP = '225.0.0.250'

import time
import struct
import socket
import sys

def main():
    addrinfo = socket.getaddrinfo(MYGROUP, None)[0]
    s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', MYPORT))
    group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])
    mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    while True:
        data, sender = s.recvfrom(1500)
        s2 = struct.Struct('d 2s f')
        unpacked_data = s2.unpack(data)
        print (str(sender) + '  ' + repr(unpacked_data))


if __name__ == '__main__':
    main()
