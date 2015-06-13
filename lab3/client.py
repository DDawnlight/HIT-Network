#!/usr/bin/env python
#coding=utf-8

import socket, os, random
import gbn

HOST = 'localhost'
PORT = 8088
BUFSIZ = 1024
ADDR = (HOST, PORT)
LOCAL_DIR = 'local'

udpCliSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

udpSender = gbn.UdpSender(udpCliSock, ADDR, timeout = 1)

udpSender.run_test()

# class FileSrc():
    # def __init__(self, filename):
        # self.filename = filename
        # self.fp = open(os.path.join(LOCAL_DIR, filename), 'r')
    # def get_data(self):
        # data = self.fp.read(1024)
        # if len(data) <= 0:
            # return False
        # return data
    # def close(self):
        # self.fp.close()

# fileHandler = FileSrc('test.jpg')

# while True:
    # # state 0
    # data = fileHandler.get_data()
    # if not data:
        # sndpkt = udpSender.make_pkt(0, '', FIN=True)
        # udpSender.udp_send(sndpkt)
        # break
    # if random.randint(0, 50) != 1:
        # sndpkt = udpSender.make_pkt(0, data)  # 发送0号分组
        # udpSender.udp_send(sndpkt)

    # # state 1
    # while not udpSender.waiting_ack(0):    # 等待确认0号分组
        # print 'resend 0'
        # sndpkt = udpSender.make_pkt(0, data)  # 重新发送0号分组
        # udpSender.udp_send(sndpkt)

    # # state 2
    # data = fileHandler.get_data()
    # if not data:
        # sndpkt = udpSender.make_pkt(0, '', FIN=True)
        # udpSender.udp_send(sndpkt)
        # break
    # if random.randint(0, 50) != 1:
        # sndpkt = udpSender.make_pkt(1, data) # 发送1号分组
        # udpSender.udp_send(sndpkt)

    # # state 3
    # while not udpSender.waiting_ack(1):    # 等待确认1号分组
        # print 'resend 1'
        # sndpkt = udpSender.make_pkt(1, data)  # 重新发送1号分组
        # udpSender.udp_send(sndpkt)

# fileHandler.close()


# if __name__ == '__main__':
    # '''
    # > upload path/to/filename server/filename
    # 上传文件

    # > download path/to/filename local/filename
    # 下载文件
    # '''
    # try:
        # while True:
            # input = raw_input('> ')
    # except KeyboardInterrupt:
        # pass
