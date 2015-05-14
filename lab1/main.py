#!/usr/bin/env python
#coding=utf-8

import threading
import socket, select
import time, base64
import os

# 版本信息
__version__ = '0.0.1'
# 代理信息
BAND = 'GFW/' + __version__

BUFFLEN = 4 * 1024 # 最大接收尺寸
TIMEOUT = 1  # 超时时间
HOST = 'localhost' # 主机名
PORT = 8808        # 端口号
EXIT_FLAG = 0      # 结束标识

Cache_dir = 'cache/'

IP_blocked = [
    '128.199.144.88',
]

restrict_users = [
    '128.199.144.88',
]

IP_allowed = [
    '192.168.',
    '127.0.0.1',
]

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
        if self.req.method == 'CONNECT':
            self._connect_handler()
        else:
            self._process_request()  # 处理请求, 发送并分析响应
            self._process_response() # 处理响应，向客户返回数据

        self.connection.close()
        exit(0)

    def _analyse_request(self):
        '''
        解析客户端请求
        '''
        while True:
            data = self.connection.recv(BUFFLEN)
            self.buff += data
            if len(data) < BUFFLEN:
                break
        # 解析
        content = self.buff.split('\r\n\r\n', 1)
        headers = content[0].split('\r\n')

        try:
            self.req.body = len(content) > 1 and content[1] or ''
            self.req.method = headers[0].split(' ')[0]
            self.req.path = headers[0].split(' ', 2)[1]
            self.req.first_line = headers[0]
        except Exception:  # 非法请求， 退出线程
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

    def _connect_handler(self):
        '''
        处理CONNECT方法， 用于https
        '''
        host = self.req.path
        i = host.find(':')
        if i!=-1:
            port = int(host[i+1:])
            host = host[:i]
        else:
            port = 80

        try:
            (family, _, _, _, address) = socket.getaddrinfo(host, port)[0]

            self._filter(address)
            print self.req.first_line

            self.target = socket.socket(family)
            self.target.connect(address)
        except socket.error:
            self.connection.send('HTTP/1.1 502 Bad gateway\r\n\r\nBad gateway\r\n')
            if hasattr(self, 'target'):
                self.target.close()
            self.connection.close()
            exit(1)

        self.connection.send('HTTP/1.1'+' 200 Connection established\n'+
                         'Proxy-agent: %s\n\n'%BAND)

        socs = [self.connection, self.target]
        timeout_max = 10

        count = 0
        while True:
            count += 1
            (recv, _, error) = select.select(socs, [], socs, 3)
            if error:
                break
            if recv:
                for in_ in recv:
                    data = in_.recv(BUFFLEN)
                    if in_ is self.connection:
                        out = self.target
                    else:
                        out = self.connection
                    if data:
                        out.send(data)
                        count = 0
            if count == timeout_max:
                break

    def _process_request(self):
        '''
        处理http请求
        '''
        pack_to_sent = ''

        # 添加 代理服务器标识
        if 'Via' in self.req.header:
            self.req.header.Via += ', 1.1 ' + BAND
        else:
            self.req.header.Via = '1.1 ' + BAND
        self.req.header.Connection = 'Close' # 非持续连接

        # 获取主机信息
        info = self.req.header.get('Host', '').split(':')
        self.req.host = info[0]
        port = len(info) > 1 and int(info[1]) or 80
        if not self.req.host: # 请求头应该包含Host属性， 如没有， 提示无法识别
            self.connection.send('HTTP/1.1 403 Forbidden\r\n\r\nRequest UnRecognize.\r\n')
            self.connection.close()
            exit(1)
        if self.req.host == HOST and port == PORT:  # 目标服务器不能是代理服务器
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
        if self.req.method == 'GET' and os.path.isfile(Cache_dir + base64.b64encode(self.req.path)):
            with open(Cache_dir + base64.b64encode(self.req.path)) as f:
                pack_to_sent += f.read().split('\r\n\r\n', 1)[0]

        for key, value in self.req.header.iteritems():
            pack_to_sent += key + ':'  + value + '\r\n'
        pack_to_sent += '\r\n'
        # 报文体
        if 'body' in self.req:
            pack_to_sent += self.req.body + '\r\n'

        try:
            (family, _, _, _, address) = socket.getaddrinfo(self.req.host, port)[0]

            self._filter(address)

            self.target = socket.socket(family)
            self.target.connect(address)
        except socket.error:
            self.connection.send('HTTP/1.1 502 Bad gateway\r\n\r\nBad gateway\r\n')
            if hasattr(self, 'target'):
                self.target.close()
            self.connection.close()
            exit(1)
        self.target.send(pack_to_sent)

        self._analyse_response()

    def _analyse_response(self):
        '''
        分析http响应报文
        '''
        # 接收服务器数据
        rec_buff = self._receive_timeout()
        if not rec_buff:
            self.connection.send('HTTP/1.1 408 Request timeout\r\n\r\nRequest timeout.\r\n');
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
            self.connection.send('HTTP/1.1 408 Request timeout\r\n\r\nRequest timeout.\r\n');
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

    def _receive_timeout(self):
        '''
        接收http响应报文
        '''
        self.target.setblocking(0)
        rec_buff = ''
        data=''

        begin=time.time()
        while True:
            # 收到一些数据，等待超时退出
            if EXIT_FLAG:
                self.connection.send('Sorry, proxy is quitted.')
                self.target.close()
                self.connection.close()
                exit(1)
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
                # self.connection.send('HTTP/1.1 502 Bad gateway\r\n\r\n');
                # self.target.close()
                # self.connection.close()
                # exit(0)

        return rec_buff

    def _process_response(self):
        '''
        处理http响应报文
        '''
        # 添加 代理服务器标识
        if 'Via' in self.res.header:
            self.res.header.Via += ', 1.1 ' + BAND
        else:
            self.res.header.Via = '1.1 ' + BAND

        # 判断是否需要进行缓存
        if self.req.method == 'GET':
            if self.res.status.startswith('304'):
                self._reply_from_cache()
            if hasattr(self.res.header, 'Last-Modified') and self.res.status.startswith('200'):
                self._cache_response()

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
        print self.req.first_line, '\033[033m', self.res.status, '\033[0m'

        self.target.close()

    def _filter(self, address):
        # 开始墙人
        if address[0] in IP_blocked:
            self.connection.send('HTTP/1.1 403 Forbidden\r\n\r\nForbidden\r\n')
            self.connection.close()
            print self.req.first_line, '\033[033m IP Blocked! \033[0m'
            exit(0)
        if self.addr[0] in restrict_users:
            if not self._ip_is_allowed(address[0]):
                self.connection.send('HTTP/1.1 303 See other\r\nLocation: http://localhost\r\nVia: 1.1 ' + BAND + '\r\n\r\n')
                self.connection.close()
                print self.req.first_line, '\033[033m User Redirected! \033[0m'
                exit(0)

    def _ip_is_allowed(self, ip):
        valid = False
        for each in IP_allowed:
            if ip.startswith(each):
                valid = True
                break
        return valid

    def _cache_response(self):
        '''
        对get 200请求进行缓存
        '''
        # 删除所有浏览器缓存相关头部
        if hasattr(self.res.header, 'ETag'):
            del self.res.header['ETag']
        if hasattr(self.res.header, 'expires'):
            del self.res.header['expires']
        if hasattr(self.res.header, 'Cache-Control'):
            del self.res.header['Cache-Control']

        with open(Cache_dir + base64.b64encode(self.req.path), 'w') as f:
            f.write('If-Modified-Since: '+ self.res.header['Last-Modified'] + '\r\n\r\n' + self.res.body)

        if hasattr(self.res.header, 'Last-Modified'):
            del self.res.header['Last-Modified']


    def _reply_from_cache(self):
        self.res.first_line = 'HTTP/1.1 200 OK from cache'
        # 删除所有浏览器缓存相关头部
        if hasattr(self.res.header, 'ETag'):
            del self.res.header['ETag']
        if hasattr(self.res.header, 'expires'):
            del self.res.header['expires']
        if hasattr(self.res.header, 'Cache-Control'):
            del self.res.header['Cache-Control']
        if hasattr(self.res.header, 'Last-Modified'):
            del self.res.header['Last-Modified']
        # try:
        print 'read', Cache_dir + base64.b64encode(self.req.path)
        with open(Cache_dir + base64.b64encode(self.req.path)) as f:
            self.res.body = f.read().split('\r\n\r\n', 1)[1]
        # except:
            # pass


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
        self.host = host
        self.addr = (host, port)
        self.timeout = timeout
        self.connections = connections
        self.hander = handler

    def run_server(self):
        tcpSerSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpSerSock.bind(self.addr)
        tcpSerSock.listen(self.connections)
        # 创建TCP服务器, 循环检查是否有请求
        print 'Proxy server is running at http://:' + self.host + ':' + str(self.addr[1])
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
            global EXIT_FLAG
            EXIT_FLAG = 1
            import sys
            sys.exit(1)

if __name__ == '__main__':
    proxySevr = ProxyServer(port = PORT, timeout = TIMEOUT)
    proxySevr.run_server()
    print 'Proxy server has exit successfully.'

