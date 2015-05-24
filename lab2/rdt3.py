#!/usr/bin/env python
#coding=utf-8

import time

BUFSIZ = 1024
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
            self.udp_send(sndpkt)

            # state 1
            while not self.waiting_ack(0):    # 等待确认0号分组
                print 'resend 0'
                sndpkt = self.make_pkt(0, 'hello')  # 发送0号分组
                self.udp_send(sndpkt)

            # state 2
            sndpkt = self.make_pkt(1, ' world') # 发送1号分组
            self.udp_send(sndpkt)

            # state 3
            while not self.waiting_ack(1):    # 等待确认1号分组
                print 'resend 1'
                sndpkt = self.make_pkt(1, ' world')  # 重新发送1号分组
                self.udp_send(sndpkt)

    def udp_send(self, data):
        '''
        使用UDP发送数据
        '''
        self.udpSendSock.sendto(data, self.addr)

    def make_pkt(self, SN, data):
        '''
        将数据打包
        SN\r\nBODY\r\n\r\n
        '''
        return str(SN) + '\r\n'+ data + '\r\n\r\n'

    def waiting_ack(self, SN):
        begin = time.time() # 启动计时器
        rec_buff = ''
        self.udpSendSock.setblocking(0)
        count = 0

        while(True):
            if '\r\n' in rec_buff:
                break
            if time.time() - begin > self.timeout:
                if rec_buff:
                    print 'ack timeout'
                    return False
                else:
                    count += 1
            if count == max_timeout:
                # 连续超时10次
                # 接收方已断开
                break
            try:
                data, ADDR = self.udpSendSock.recvfrom(BUFSIZ)
                if data:
                    rec_buff += data
                    begin = time.time()
                else:
                    break
            except Exception:
                time.sleep(0.01)
        # print rec_buff
        '''
        报文格式
        ACK SN\r\n
        '''
        res = rec_buff[:-2].split(' ')

        if len(res) >= 2 and res[0] == 'ACK' and res[1] == str(SN):
            return True
        else:
            return False


class UdpReceiver(object):
    def __init__(self, udpRecevSock, timeout = 0.5):
        self.udpRecevSock = udpRecevSock
        self.timeout = timeout

    def run_test(self):
        while True:
            while not self.waiting_for(0): # 等待接受0号分组
                nak_pck = self.make_pkt(0)
                self.udpRecevSock.sendto(nak_pck, self.target)

            ack_pck = self.make_pkt(0, True) # 发送0号分组的确认
            self.udpRecevSock.sendto(ack_pck, self.target)

            while not self.waiting_for(1): # 等待接收1号分组
                nak_pck = self.make_pkt(1)
                self.udpRecevSock.sendto(nak_pck, self.target)

            ack_pck = self.make_pkt(1, True) # 发送1号分组的确认
            self.udpRecevSock.sendto(ack_pck, self.target)

    def waiting_for(self, SN):
        '''
        接收方等待接受SN分组
        '''
        rec_buff = ''
        self.udpRecevSock.setblocking(0)
        start = time.time()
        count = 0

        while(True):
            try:
                if '\r\n\r\n' in rec_buff:
                    break
                if time.time() - start > self.timeout:
                    if rec_buff:
                        print 'package timeout'
                        return False
                    else:
                        count += 1
                if count  == max_timeout:
                    # 连续超时十次
                    # 重置连接
                    # reset
                    pass
                data, ADDR = self.udpRecevSock.recvfrom(BUFSIZ)
                self.target = ADDR
                if data:
                    rec_buff += data
                else:
                    break
            except:
                time.sleep(0.01)
        # print rec_buff
        '''
        报文格式
        SN\r\nBODY\r\n\r\n
        '''
        req = rec_buff[:-4].split('\r\n')
        if len(req) >= 2 and req[0] == str(SN):
            '''
            收到SN号报文
            这里进行对报文的处理
            '''
            body = req[1]
            print body
            return True
        else:
            return False

    def make_pkt(self, SN, isACK = False):
        '''
        创建确认报文
        ACK SN\r\n
        '''
        message = 'ACK' if isACK else 'NAK'
        message += ' ' + str(SN) + '\r\n'
        return message

if __name__ == '__main__':
    HOST = ''
    PORT = 8088
    BUFSIZ = 1024
    ADDR = (HOST, PORT)

    import socket
    udpSerSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udpSerSock.bind(ADDR)
    print 'Server is running at', ADDR

    UdpReceiver(udpSerSock).run_test()

