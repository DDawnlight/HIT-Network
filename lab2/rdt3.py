#!/usr/bin/env python
#coding=utf-8

import struct, random
import socket

BUFSIZ = 4096
max_timeout = 10


class UdpSender(object):
    def __init__(self, udpSendSock, ADDR, timeout = 1):
        self.timeout = timeout
        self.udpSendSock = udpSendSock
        self.addr = ADDR

    def run_test(self):
        '''
        状态:
            0: 等待发送0号分组
            1: 等待0号分组确认
            2: 等待发送1号分组
            3: 等待1号分组确认
        '''
        while True:
            # state 0
            sndpkt = self.make_pkt(0, 'hello')  # 发送0号分组
            if random.randint(0, 10) != 1:
                self.udp_send(sndpkt)

            # state 1
            while not self.waiting_ack(0):    # 等待确认0号分组
                # print 'resend 0'
                sndpkt = self.make_pkt(0, 'hello')  # 重新发送0号分组
                self.udp_send(sndpkt)

            # state 2
            sndpkt = self.make_pkt(1, ' world') # 发送1号分组
            self.udp_send(sndpkt)

            # state 3
            while not self.waiting_ack(1):    # 等待确认1号分组
                # print 'resend 1'
                sndpkt = self.make_pkt(1, ' world')  # 重新发送1号分组
                self.udp_send(sndpkt)

    def udp_send(self, data):
        '''
        使用UDP发送数据
        '''
        self.udpSendSock.sendto(data, self.addr)

    def make_pkt(self, SN, data, FIN=False, ACK=False):
        '''
        将数据打包
        ack|ack_num|seq|seq_num|fin
        7  |   6   | 5 |  4    | 3
        BODY
        '''
        state = 0|0b100000 if not FIN else 0|0b1000
        state = state|0b10000 if not FIN and SN else state
        return struct.pack('B', state) + data

    def waiting_ack(self, SN):
        self.udpSendSock.settimeout(self.timeout)
        count = 0

        while(True):
            if count >= max_timeout:
                # 连续超时10次
                # 接收方已断开
                break
            try:
                data, ADDR = self.udpSendSock.recvfrom(BUFSIZ)
                self.target = ADDR

                ack, ack_num, seq, seq_num, fin, data = self.analysis_pkt(data)
                if ack and int(ack_num) == SN:
                    # 已被正确接收
                    return True
                else:
                    return False
            except socket.timeout:
                return False

    def analysis_pkt(self, pkt):
        '''
        将数据打包
        ack|ack_num|seq|seq_num|fin
        7  |   6   | 5 |  4    | 3
        BODY
        '''
        state = struct.unpack('B', pkt[0])[0]
        data = pkt[1:]
        fin = state&0b1000
        seq_num = (state&0b10000)>>4
        seq = state&0b100000
        ack_num = (state&1000000)>>6
        ack = state&10000000
        return ack, ack_num, seq, seq_num, fin, data


class UdpReceiver(object):
    def __init__(self, udpRecevSock, timeout = 0.5, max_repeat = 20):
        self.udpRecevSock = udpRecevSock
        self.timeout = timeout
        self.max_repeat = max_repeat  # 最大分组

    def run_test(self):
        while True:
            while not self.waiting_for(0): # 等待接受0号分组
                continue

            while not self.waiting_for(1): # 等待接收1号分组
                continue

    def waiting_for(self, SN):
        '''
        接收方等待接受SN分组
        '''
        self.udpRecevSock.settimeout(self.timeout)
        count = 0

        while(True):
            try:
                if count  >= max_timeout:
                    # 连续超时十次  重置连接  reset
                    pass
                data, ADDR = self.udpRecevSock.recvfrom(BUFSIZ)
                self.target = ADDR

                ack, ack_num, seq, seq_num, fin, data = self.analysis_pkt(data)
                if fin:
                    # 传输结束
                    return None,True
                if seq:
                    ack_pck = self.make_pkt(seq_num, True) # 发送分组的确认
                    self.udpRecevSock.sendto(ack_pck, self.target)
                    if int(seq_num) == SN:
                        return data, False
                    else:
                        return False, False
                else:
                    nak_pkt = self.make_pkt()
                    self.udpRecevSock.sendto(nak_pkt, self.target)
            except socket.timeout:
                '''
                timeout
                '''
                return False, False

    def analysis_pkt(self, pkt):
        '''
        分析数据
        ack|ack_num|seq|seq_num|fin
        7  |   6   | 5 |  4    | 3
        BODY
        '''
        state = struct.unpack('B', pkt[0])[0]
        data = pkt[1:]
        fin = state&0b1000
        seq_num = (state&0b10000)>>4
        seq = state&0b100000
        ack_num = (state&1000000)>>6
        ack = state&10000000
        return ack, ack_num, seq, seq_num, fin, data

    def make_pkt(self, SN = 0, isACK = False):
        '''
        创建确认报文
        ack|ack_num|seq|seq_num|fin
        7  |   6   | 5 |  4    | 3
        BODY
        '''
        state = 0b10000000 if isACK else 0
        state = state|0b01000000 if isACK and SN else state
        return struct.pack('B', state)

