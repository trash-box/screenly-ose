#!/usr/bin/env python
# -*- coding: utf-8 -*-

# https://wiki.pythonde.pysv.org/UDP-Broadcasts

import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
s.settimeout(5)

x = "010000000000000044000000340000004d3c2b1ae1da44300000000034000000000000000010000000aa0000000a000004000000c8000000040a000004000000ffffff00"

s.sendto(bytearray.fromhex(x), ("<broadcast>", 42000))
try:
    print("Response: %s" % s.recv(1024))
except socket.timeout:
    print("No server found")

s.close()