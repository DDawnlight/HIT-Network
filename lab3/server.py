#!/usr/bin/env python
#coding=utf-8

import socket, os, time
import sr

HOST = ''
PORT = 8088
BUFSIZ = 1024
ADDR = (HOST, PORT)
SEVER_DIR = 'server'

udpSerSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udpSerSock.bind(ADDR)

udpReceiver = sr.UdpReceiver(udpSerSock)

class FileSaver():
    def __init__(self, filename):
        self.filename = filename
        self.fp  = open(os.path.join(SEVER_DIR, filename), 'w+')


    def close(self):
        self.fp.close()

def get_filename(suffix = '.jpg'):
    return str(int(time.time())) + suffix

fileSaver = FileSaver(get_filename())
def save_data(data, fp):
    print 'got data length:', len(data)
    fp.write(data)

reset = False

while True:
    if reset:
        fileSaver.close()
        fileSaver = FileSaver(get_filename())
        udpReceiver.recv_base = 0
        for i in range(256):
            udpReceiver.rcvs[i] = ''
        reset = False
    while True:
        reset = udpReceiver.waiting_for(lambda data: save_data(data, fileSaver.fp))
        if reset: break
    if reset: continue

fileSaver.close()
