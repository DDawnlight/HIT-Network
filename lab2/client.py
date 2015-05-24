#!/usr/bin/env python
#coding=utf-8

import socket
import rdt3

HOST = 'localhost'
PORT = 8088
BUFSIZ = 1024
ADDR = (HOST, PORT)

udpCliSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

rdt3.UdpSender(udpCliSock, ADDR, timeout = 1).run_test()

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
