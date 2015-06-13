#!/usr/bin/env python
#coding=utf-8

import socket, os, time
import rdt3

HOST = ''
PORT = 8088
BUFSIZ = 1024
ADDR = (HOST, PORT)
SEVER_DIR = 'server'

udpSerSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udpSerSock.bind(ADDR)

udpReceiver = rdt3.UdpReceiver(udpSerSock)

class FileSaver():
    def __init__(self, filename):
        self.filename = filename
        self.fp  = open(os.path.join(SEVER_DIR, filename), 'w+')

    def save_data(self, data):
        self.fp.write(data)

    def close(self):
        self.fp.close()

def get_filename(suffix = '.jpg'):
    return str(int(time.time())) + suffix

fileSaver = FileSaver(get_filename())
reset = 0

while True:
    if reset:
        fileSaver.close()
        fileSaver = FileSaver(get_filename())
        reset = 0
    while True:  # 等待接受0号分组
        data, reset = udpReceiver.waiting_for(0)
        if data:
            fileSaver.save_data(data)
            break
        if reset: break
    if reset: continue

    while True: # 等待接收1号分组
        data, reset = udpReceiver.waiting_for(1)
        if data:
            fileSaver.save_data(data)
            break
        if reset: break
    if reset: continue

fileSaver.close()
