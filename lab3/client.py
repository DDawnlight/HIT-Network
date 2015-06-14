#!/usr/bin/env python
#coding=utf-8

import socket, os
import sr

HOST = 'localhost'
PORT = 8088
BUFSIZ = 1024
ADDR = (HOST, PORT)
LOCAL_DIR = 'local'

udpCliSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

udpSender = sr.UdpSender(udpCliSock, ADDR, timeout = 1, loss_rate = 0.1)

class FileSrc():
    def __init__(self, filename):
        self.filename = filename
        self.fp = open(os.path.join(LOCAL_DIR, filename), 'r')
    def get_data(self):
        data = self.fp.read(1024)
        if len(data) <= 0:
            return False
        return data
    def close(self):
        self.fp.close()

fileHandler = FileSrc('hello.jpg')

while True:
    while udpSender.next_seq < udpSender.send_base+udpSender.window_size:
        # 发送窗口未被占满
        data = fileHandler.get_data()
        if not data:
            udpSender.pkts[udpSender.next_seq] = udpSender.make_pkt(udpSender.next_seq, '', FIN=True)
            break
        else:
            udpSender.pkts[udpSender.next_seq] = udpSender.make_pkt(udpSender.next_seq, data)
        print 'send pkt:', udpSender.next_seq
        udpSender.udp_send(udpSender.pkts[udpSender.next_seq])
        udpSender.next_seq = (udpSender.next_seq+1)%256
    if not data:
        break

    udpSender.waiting_ack()

fileHandler.close()


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
