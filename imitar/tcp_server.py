# Copyright 2015 jydo inc. All rights reserved.
from logging import getLogger, StreamHandler, DEBUG, INFO
from queue import Queue, Empty
import socket
import threading
import sys
import errno


logger = getLogger('tcp_server')
logger.addHandler(StreamHandler(stream=sys.stdout))


class ClientDisconnectedError(Exception):
    pass


class ClientWorker:
    def __init__(self, client_queue, broadcast_queue, handle_message, delimiter, encoding=None, welcome_message=None):
        self.client_queue = client_queue
        self.broadcast_queue = broadcast_queue
        self.handle_message = handle_message
        self.delimiter = delimiter
        self.encoding = encoding
        self.welcome_message = welcome_message
        self.message_queue = Queue()
        self.buffer = bytearray()
        self.client = None
        self.address = None
        self._stop = False
        self.thread = threading.Thread(target=self.run_loop, daemon=False)
        self.thread.start()

    def on_client_disconnect(self):
        if self.client is not None:
            logger.debug('{} disconnected, cleaning up.'.format(self.address))
            self.client.close()
            self.client = None

        self.address = None
        self.buffer = bytearray()

    def receive_data(self):
        incoming = b''

        try:
            incoming = self.client.recv(4096)
        except socket.timeout:
            # This is ok
            return
        except socket.error:
            # This will be taken care of by checking the length of incoming below.
            pass

        if len(incoming) == 0:
            self.on_client_disconnect()
            raise ClientDisconnectedError('Client {} disconnected')

        self.buffer.extend(incoming)
        logger.debug('buffer: {}'.format(self.buffer))
        messages = self.buffer.split(self.delimiter)

        # If the last character received was a delimiter then the last message is an empty bytearray, otherwise it's an
        # incomplete message, either way we don't want it in the messages array.
        self.buffer = messages.pop(-1)

        if self.encoding:
            decoded_messages = []

            for message in messages:
                if message != b'':
                    decoded_messages.append(message.decode(self.encoding))

            messages = decoded_messages

        for message in messages:
            if message != b'':
                response = self.handle_message(message)
                broadcast = True

                if type(response) == tuple:
                    response, broadcast = response

                if response is None:
                    continue

                self.message_queue.put(response)

                if broadcast:
                    self.broadcast_queue.put((response, self))

    def send_message(self, message):
        if self.client is not None:
            if self.encoding:
                message = message.encode(self.encoding)

            message = message + self.delimiter

            self.client.sendall(message)

    def send_pending_messages(self):
        while not self.message_queue.empty():
            self.send_message(self.message_queue.get())

    def run_loop(self):
        while not self._stop:
            if self.client is None:
                try:
                    self.client, self.address = self.client_queue.get(timeout=0.5)

                    if self.welcome_message is not None:
                        self.client.sendall(self.welcome_message + self.delimiter)
                except Empty:
                    continue

            try:
                self.receive_data()
            except ClientDisconnectedError:
                # If the client disconnects then self.client is None and the message queue is cleared, so no need
                # to continue to send_pending_messages
                continue
            except Exception as e:
                # TODO: should we consider the connection dead at this point?
                logger.exception('Error during receive_data: {}'.format(e))

            try:
                self.send_pending_messages()
            except Exception as e:
                # TODO: should we consider the connection dead at this point?
                logger.exception('Error during send_data: {}'.format(e))

        self.on_client_disconnect()

    def close(self):
        if self.client:
            self.on_client_disconnect()

    def stop(self):
        logger.debug('Stopping client worker {}'.format(self.thread.ident))
        self._stop = True


class TcpServer:
    """
    Used to create some mock network services that emulate real devices. Allows us to test our transports without having
    access to a real device. This transport emulates a more advanced type of device that can handle more than one
    connection at a time and pushes data. If we want to emulate a shitty device that only accepts one connection at a
    time we'll need to create a new server type.

    TODO: Find a way to prompt for login/password per client. This means we'll need some sort of session object that
          will probably have to be passed to the handle_messages callback.
    """
    def __init__(self, port, handle_message, encoding='ascii', delimiter='\r\n', welcome_message=None, debug=False):
        self.port = port
        self.handle_message = handle_message
        self.encoding = encoding
        self.delimiter = delimiter
        self.welcome_message = welcome_message
        self.debug = debug
        self.broadcast_queue = Queue()
        self.client_queue = Queue()
        self.client_workers = []
        self.socket = None
        self.accept_thread = threading.Thread(target=self.accept_loop, daemon=False)
        self.client_thread = threading.Thread(target=self.broadcast_loop, daemon=False)
        self._shutting_down = False

        if self.encoding:
            self.delimiter = self.delimiter.encode(self.encoding)

            if welcome_message is not None:
                self.welcome_message = self.welcome_message.encode(self.encoding)

        if self.debug:
            logger.setLevel(DEBUG)
        else:
            logger.setLevel(INFO)

    def create_server_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', self.port))
        sock.listen(5)
        self.socket = sock

    def create_workers(self):
        for i in range(0, 4):
            worker = ClientWorker(self.client_queue, self.broadcast_queue, self.handle_message, self.delimiter,
                                  self.encoding, self.welcome_message)
            self.client_workers.append(worker)

    def broadcast_message(self, message, from_worker=None):
        for worker in self.client_workers:
            # Only broadcast to workers that aren't the one that sent the message.
            if from_worker is None or worker != from_worker:
                worker.send_message(message)

    def broadcast_loop(self):
        while not self._shutting_down:
            try:
                self.broadcast_message(*self.broadcast_queue.get(timeout=0.5))
            except Empty:
                # This is normal
                pass

    def accept_client(self, client, address):
        logger.debug('Accepting connection from {}'.format(address))
        client.settimeout(0.2)
        self.client_queue.put((client, address))

    def accept_loop(self):
        while not self._shutting_down:
            try:
                self.accept_client(*self.socket.accept())
            except socket.error as err:
                logger.error('Error accepting a client socket: {}'.format(err))

    def start(self):
        self.create_server_socket()
        self.create_workers()
        self.accept_thread.start()
        self.client_thread.start()

    def shutdown(self):
        self._shutting_down = True

        logger.debug('Stopping workers')
        for worker in self.client_workers:
            worker.stop()

        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except socket.error as err:
            if err.errno != errno.ENOTCONN:
                logger.debug('Failed to shut down socket. {}'.format(err))
        finally:
            self.socket.close()

    def close_all_clients(self):
        """
        Use this to close all the clients without shutting the server down. i.e. to emulate something like a Samsung DMD
        that closes all connections during power on.
        :return:
        """
        for worker in self.client_workers:
            worker.close()
