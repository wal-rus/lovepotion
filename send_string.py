#!/usr/bin/env python
# Sends a string over TCP connection.

from __future__ import print_function

import socket

class SendString(object):
    """Class that sends strings over a TCP connection."""

    def __init__(self, host, port):
        self._host = host
        self._port = port

    def Send(self, what):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self._host, self._port))
            s.send(what)
            s.close()
        except socket.error, e:
            print('Socket comms failed: %s' % e)


if __name__ == '__main__':
    s = SendString('192.168.1.17', 4000)
    s.Send('foo')
