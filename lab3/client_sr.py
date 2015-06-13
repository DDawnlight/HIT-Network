#!/usr/bin/env python
#coding=utf-8

import socket
import sr

HOST = 'localhost'
PORT = 8088
BUFSIZ = 1024
ADDR = (HOST, PORT)
LOCAL_DIR = 'local'

udpCliSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

udpSender = sr.UdpSender(udpCliSock, ADDR, timeout = 1, loss_rate = 0.1)

udpSender.run_test()

