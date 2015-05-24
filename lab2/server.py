#!/usr/bin/env python
#coding=utf-8

import socket
import rdt3

HOST = ''
PORT = 8088
BUFSIZ = 1024
ADDR = (HOST, PORT)

udpSerSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udpSerSock.bind(ADDR)

rdt3.UdpReceiver(udpSerSock).run_test()

