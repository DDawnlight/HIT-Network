#!/usr/bin/env python
#coding=utf-8

import socket
import gbn

'''
GBN 协议验证 -- 发送方部分
'''

HOST = 'localhost'
PORT = 8088
BUFSIZ = 1024
ADDR = (HOST, PORT)
LOCAL_DIR = 'local'

udpCliSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

udpSender = gbn.UdpSender(udpCliSock, ADDR, timeout = 1, loss_rate = 0.1)

udpSender.run_test()

