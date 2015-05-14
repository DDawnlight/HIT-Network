#!/usr/bin/env python
#coding=utf-8

import threading
import socket
import string, time

__version__ = '0.0.1'
BAND = 'GFW/' + __version__
BUFFLEN = 4 * 1024
TIMEOUT = 1
HOST = 'localhost'
PORT = 8808

class Storage(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError, k:
            raise AttributeError, k

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k

    def __repr__(self):
        return '<Storage ' + dict.__repr__(self) + '>'


class ConnectionHandler(object):
    '''
    请求处理类
    '''
    def __init__(self, tcpCliSock, addr, timeout = 2):
        self.connection = tcpCliSock
        self.addr = addr
        self.buff = ''
        self.timeout = timeout
        self.req = Storage()
        self.res = Storage()

        self._analyse_request()  # 分析请求
        self._process_request()  # 处理请求, 发送并分析响应
        self._process_response() # 处理响应，向客户返回数据

        self.connection.close()

    def _analyse_request(self):
        while True:
            data = self.connection.recv(BUFFLEN)
            self.buff += data
            if len(data) < BUFFLEN:
                break
        # 解析
        content = self.buff.split('\r\n\r\n', 1)
        headers = content[0].split('\r\n')

        try:

            self.req.body = content[1]
            self.req.method = headers[0].split(' ')[0]
            self.req.first_line = headers[0]
        except Exception:  # 非法请求， 退出线程
            print "Invalid Request"
            self.connection.send('HTTP/1.1 403 Forbidden\r\n\r\nInvalid Request!\r\n')
            self.connection.close()
            exit(0)

        self.req.header = Storage()

        for each_item in headers[1:]:
            l = each_item.split(':', 1)
            if len(l) < 2:
                continue
            attr = l[0].strip()
            value = l[1].strip()
            self.req.header[attr] = value

    def _process_request(self):
        pack_to_sent = ''

        # 添加 代理服务器标识
        if 'Via' in self.req.header:
            self.req.header.Via += ', 1.1 ' + BAND
        else:
            self.req.header.Via = '1.1 ' + BAND
        self.req.header.Connection = 'Close' # 非持续连接

        # 获取主机信息
        info = self.req.header.get('Host', '').split(':')
        host = info[0]
        port = len(info) > 1 and string.atoi(info[1]) or 80
        if not host: # 请求头应该包含Host属性， 如没有， 提示无法识别
            self.connection.send('HTTP/1.1 403 Forbidden\r\n\r\nRequest UnRecognize.\r\n')
            print "Request UnRecognize."
            self.connection.close()
            exit(1)
        if host == HOST and port == PORT:  # 目标服务器不能是代理服务器
            print "Invalid Request"
            self.connection.send('HTTP/1.1 403 Forbidden\r\n\r\nInvalid Request!\r\n')
            self.connection.close()
            exit(0)

        #  构造报文 起始行
        pack_to_sent = self.req.first_line + '\r\n'
        # Host 字段
        if 'Host' in self.req.header:
            pack_to_sent += 'Host: ' + self.req.header['Host'] + '\r\n'
            del self.req.header['Host']
        # 报文头
        for key, value in self.req.header.iteritems():
            pack_to_sent += key + ':'  + value + '\r\n'
        pack_to_sent += '\r\n'
        # 报文体
        if 'body' in self.req:
            pack_to_sent += self.req.body + '\r\n'

        (family, _, _, _, address) = socket.getaddrinfo(host, port)[0]
        self.target = socket.socket(family)
        try:
            self.target.connect(address)
        except socket.error:
            self.connection.send('HTTP/1.1 504 Gateway timeout\r\n\r\nGateway timeout\r\n')
            self.target.close()
            self.connection.close()
            exit(1)
        self.target.send(pack_to_sent)

        self._analyse_response()

    def _analyse_response(self):
        # 接收服务器数据
        rec_buff = self._receive_timeout()
        if not rec_buff:
            self.connection.send('HTTP/1.1 408 Request timeout\r\n\r\nrequest timeout.\r\n');
            self.target.close()
            self.connection.close()
            exit(0)

        content = rec_buff.split('\r\n\r\n', 1)
        headers = content[0].split('\r\n')
        try:
            self.res.body = content[1]
            self.res.status = headers[0].split(' ', 1)[1]
            self.res.first_line = headers[0]
            self.res.header = Storage()
        except Exception:  # 返回的信息不完整或者格式错误, 算作超时
            self.connection.send('HTTP/1.1 408 Request timeout\r\n\r\nrequest timeout.\r\n');
            self.target.close()
            self.connection.close()
            exit(0)

        for each_item in headers[1:]:
            l = each_item.split(':', 1)
            if len(l) < 2:
                continue
            attr = l[0].strip()
            value = l[1].strip()
            self.res.header[attr] = value

        # 添加 代理服务器标识
        if 'Via' in self.res.header:
            self.res.header.Via += ', 1.1 ' + BAND
        else:
            self.res.header.Via = '1.1 ' + BAND


        #  构造报文 起始行
        reply_pack = self.res.first_line + '\r\n'
        # 报文头
        for key, value in self.res.header.iteritems():
            reply_pack += key + ':'  + value + '\r\n'
        reply_pack += '\r\n'
        reply_pack += self.res.get('body', '')

        # 发送响应报文头
        self.connection.send(reply_pack)
        # 发送响应报文体
        print self.req.first_line, self.res.status

        self.target.close()

    def _receive_timeout(self):

        #non blocking
        self.target.setblocking(0)
        rec_buff = ''
        data=''

        begin=time.time()
        while 1:
            # 收到一些数据，等待超时退出
            if rec_buff and time.time()-begin > self.timeout:
                break
            # 没有收到数据， 稍微等会
            elif time.time()-begin > self.timeout*2:
                break
            try:
                data = self.target.recv(BUFFLEN)
                if data:
                    rec_buff += data
                    begin=time.time() # 更新接收开始时间
                else:
                    time.sleep(0.1)
            except:
                pass

        return rec_buff

    def _process_response(self):
        pass


class ProxyServer(object):
    '''
    代理服务器类
    '''
    def __init__(self, host = HOST, port = PORT, connections = 50,
                 timeout=TIMEOUT, handler = ConnectionHandler):
        '''
        配置代理服务器主机, 端口, 最大连接数
        请求处理函数的等信息
        '''
        self.addr = (host, port)
        self.timeout = timeout
        self.connections = connections
        self.hander = handler

    def run_server(self):
        tcpSerSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpSerSock.bind(self.addr)
        tcpSerSock.listen(self.connections)
        # 创建TCP服务器, 循环检查是否有请求
        print 'Proxy server is running at http://localhost:' + str(self.addr[1])
        try:
            while True:
                tcpCliSock, addr = tcpSerSock.accept()  # 收到请求
                t = threading.Thread(target = ConnectionHandler,\
                    args=(tcpCliSock, addr), kwargs=dict(timeout = self.timeout))  # 创建线程处理请求
                t.start()
        except KeyboardInterrupt, err:
            print err
        except Exception:
            pass
        finally:
            tcpSerSock.close()
            print 'Proxy server has exit successfully.'
            import sys
            sys.exit(1)

if __name__ == '__main__':
    proxySevr = ProxyServer(port = PORT, timeout = TIMEOUT)
    proxySevr.run_server()

