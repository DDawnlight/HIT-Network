#!/usr/bin/env python
#coding=utf-8

import struct, random
import socket, time

BUFSIZ = 4096
max_timeout = 10


class UdpSender(object):
    def __init__(self, udpSendSock, ADDR, timeout = 1, window_size = 4, loss_rate = 0):
        self.timeout = timeout
        self.udpSendSock = udpSendSock
        self.addr = ADDR
        self.loss_rate = loss_rate
        self.window_size = window_size
        self.send_base = 0
        self.next_seq = 0
        self.pkts = []
        for i in range(256):
            self.pkts.append('')

    def run_test(self):
        '''
        '''
        while True:
            while self.next_seq < self.send_base+self.window_size:
                # 发送窗口未被占满
                self.pkts[self.next_seq] = self.make_pkt(self.next_seq, str(time.time())+' '+str(self.next_seq))
                print 'send pkt: ', self.next_seq
                # if random.randint(0, 100) != 1:
                self.udp_send(self.pkts[self.next_seq])
                self.next_seq = (self.next_seq+1)%256

            self.waiting_ack()

    def udp_send(self, data):
        '''
        使用UDP发送数据
        '''
        if self.loss_rate == 0 or random.randint(0, int(1/self.loss_rate)) != 1:
            self.udpSendSock.sendto(data, self.addr)
        else:
            print "Loss: ", data
        time.sleep(0.3)


    def waiting_ack(self):
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

                (ack, ack_num, seq, seq_num, fin, window_size, data) = self.analysis_pkt(data)
                if ack : # 收到确认
                    if(self.send_base == (ack_num+1) % 256):
                        # 收到重复确认, 此处应当立即重发
                        pass
                        # for i in range(self.send_base, self.next_seq):
                            # print 'resend pkt: ', i
                            # self.udp_send(self.pkts[i])

                    self.send_base = max(self.send_base, (ack_num+1)%256)
                    if(self.send_base == self.next_seq): # 已发送分组确认完毕
                        self.udpSendSock.settimeout(None)
                        return True
            except socket.timeout:
                # 超时，重发分组.
                print 'timeout.'
                for i in range(self.send_base, self.next_seq):
                    print 'resend pkt: ', i
                    self.udp_send(self.pkts[i])
                self.udpSendSock.settimeout(self.timeout) # reset timer

    def make_pkt(self, SN, data, FIN=False, ACK=False):
        '''
        将数据打包
        |7  |   6   | 5 |  4    | 3 |210|
        |           ack_seq             |
        |           package_seq         |
        |               |    ack|seq|fin|
        |          window_size          |
        BODY
        '''
        state = 0b11 if FIN else 0b10
        return struct.pack('BBBB', 0, SN, state, self.window_size) + data

    def analysis_pkt(self, pkt):
        '''
        分析数据
        |7  |   6   | 5 |  4    | 3 |210|
        |           ack_seq             |
        |           package_seq         |
        |               |    ack|seq|fin|
        |          window_size          |
        BODY
        '''
        ack_num = struct.unpack('B', pkt[0])[0]
        seq_num = struct.unpack('B', pkt[1])[0]
        state = struct.unpack('B', pkt[2])[0]
        window_size = struct.unpack('B', pkt[3])[0]
        data = pkt[3:]
        fin = state&0b1
        seq = state&0b10
        ack = state&0b100
        return ack, ack_num, seq, seq_num, fin, window_size, data


class UdpReceiver(object):
    def __init__(self, udpRecvSock, window_size = 200, timeout = 0.5, max_repeat = 20, loss_rate = 0):
        self.udpRecvSock = udpRecvSock
        self.window_size = window_size
        self.timeout = timeout
        self.max_repeat = max_repeat  # 最大分组
        self.loss_rate = loss_rate
        self.expectseq = 0

    def run_test(self):
        reset = False
        while True:
            if reset:
                self.expectseq = 0
                reset = False
            while True:
                data, reset = self.waiting_for(self.expectseq)
                if data:
                    print 'Got Data:', data
                    break
                if reset: break
            if reset: continue

    def udp_send(self, data):
        '''
        使用UDP发送数据
        '''
        if self.loss_rate == 0 or random.randint(0, 1/self.loss_rate) != 1:
            self.udpRecvSock.sendto(data, self.target)
        else:
            print "Loss: ", data

    def waiting_for(self, SN):
        '''
        接收方等待接受SN分组
        '''
        self.udpRecvSock.settimeout(self.timeout)
        count = 0

        while(True):
            try:
                if count  >= max_timeout:
                    # 连续超时十次  重置连接  reset
                    pass
                data, ADDR = self.udpRecvSock.recvfrom(BUFSIZ)
                self.target = ADDR

                (ack, ack_num, seq, seq_num, fin, window_size, data) = self.analysis_pkt(data)
                self.window_size = window_size
                if fin:
                    # 传输结束
                    return None,True
                if seq and seq_num == SN:
                    self.expectseq = (self.expectseq + 1) % 256

                ack_pkt = self.make_pkt((self.expectseq-1) % 256, True)
                self.udp_send(ack_pkt)
                # self.udpRecvSock.sendto(ack_pkt, self.target)
                print time.time(), 'send ack: ', (self.expectseq-1)%256

                if seq and seq_num == SN:
                    return data, False
                else:
                    return None, False

            except socket.timeout:
                '''
                timeout
                '''
                return None, False

    def analysis_pkt(self, pkt):
        '''
        分析数据
        |7  |   6   | 5 |  4    | 3 |210|
        |           ack_seq             |
        |           package_seq         |
        |               |    ack|seq|fin|
        |          window_size          |
        BODY
        '''
        # if len(pkt) < 4:
            # print 'Invalid Packet'
            # return False
        ack_num = struct.unpack('B', pkt[0])[0]
        seq_num = struct.unpack('B', pkt[1])[0]
        state = struct.unpack('B', pkt[2])[0]
        window_size = struct.unpack('B', pkt[3])[0]
        data = pkt[3:]
        fin = state&0b1
        seq = state&0b10
        ack = state&0b100
        return ack, ack_num, seq, seq_num, fin, window_size, data

    def make_pkt(self, SN = 0, isACK = False, seq_num = 0):
        '''
        创建确认报文
        |7  |   6   | 5 |  4    | 3 |210|
        |           ack_seq             |
        |           package_seq         |
        |               |    ack|seq|fin|
        |          window_size          |
        BODY
        '''
        state = 0b100 if isACK else 0
        # print type(SN)
        # print type(seq_num)
        # print type(state)
        # print type(self.window_size)
        # print self.window_size

        return struct.pack('BBBB', SN, seq_num, state, self.window_size)

if __name__ == '__main__':
    HOST = ''
    PORT = 8088
    BUFSIZ = 1024
    ADDR = (HOST, PORT)
    SEVER_DIR = 'server'

    udpSerSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udpSerSock.bind(ADDR)

    UdpReceiver(udpSerSock).run_test()
