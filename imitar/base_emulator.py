# Copyright 2015 jydo inc. All rights reserved.
from abc import ABCMeta, abstractmethod
from logging import getLogger, StreamHandler, DEBUG, INFO
import sys
import signal
from .tcp_server import TcpServer


_logger = getLogger('device_server')
_logger.addHandler(StreamHandler(stream=sys.stdout))


class BaseEmulator(metaclass=ABCMeta):
    welcome_message = None
    logger = _logger

    def __init__(self, port, encoding='ascii', delimiter='\r\n', debug=False):
        self.port = port
        self.debug = debug
        self.transport = TcpServer(self.port, self.handle_message, encoding, delimiter, self.welcome_message, debug)
        self._init_shutdown()

        if debug:
            self.logger.setLevel(DEBUG)
        else:
            self.logger.setLevel(INFO)

    def start(self):
        self.transport.start()

    def shutdown(self, signum, sigframe):
        self.transport.shutdown()
        sys.exit(0)

    def _init_shutdown(self):
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    @abstractmethod
    def handle_message(self, message) -> tuple:
        """
        This is where you handle incoming messages from connected clients. Return a tuple of (response, broadcast). If
        broadcast is True the response  will be sent to all connected clients.

        :param message:
        :return: tuple(response, broadcast: bool)
        """
        pass
