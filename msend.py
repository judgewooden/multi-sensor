#!/usr/bin/env python
#
# Send to multicast address

MYPORT = 8123
MYGROUP = '225.0.0.250'

import time
import struct
import socket
import sys
import os

def main():
    addrinfo = socket.getaddrinfo(MYGROUP, None)[0]
    s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
    while True:
        data = repr(time.time())
        f = os.popen('/bin/cat /sys/class/thermal/thermal_zone0/temp')
        piTemp=float(f.read())
        values = (time.time(), "A1", piTemp)
        print (values)
        packer = struct.Struct('d 2s f')
        packed_data = packer.pack(*values)
        piSend = repr(piTemp)
        s.sendto(packed_data, (addrinfo[4][0], MYPORT))
        time.sleep(.1)


if __name__ == '__main__':
    main()
