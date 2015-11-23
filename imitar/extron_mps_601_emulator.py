# Copyright 2015 jydo inc. All rights reserved.
from logging import StreamHandler
from logging import getLogger
import sys
from imitar.base_emulator import BaseEmulator
from imitar.message_parser import CharacterMessageParser

__version__ = '1.0.0'
_logger = getLogger('extron_emulator')
_logger.addHandler(StreamHandler(stream=sys.stdout))
DELIMITER = '\r\n'
ENCODING = 'ascii'


class ExtronMps601Emulator(BaseEmulator):
    logger = _logger
    message_parser = CharacterMessageParser(DELIMITER, ENCODING)

    def __init__(self, port, debug=False):
        super().__init__(port, self.message_parser, 'ascii', '\r\n', debug=debug)
        self.connection_state = [1, 1, 1, 1, 1, 1, 1]
        self.active_input = 1
        self.auto_switch_mode = 0

    def handle_input(self, message):
        broadcast = True

        if message[0].isnumeric():
            if self.auto_switch_mode == 0:
                active_input = int(message[0])
                self.active_input = active_input
                resp = 'In{} All'.format(active_input)
            else:
                resp = 'E06'
                broadcast = False
        else:
            broadcast = False
            resp = str(self.active_input)

        return resp, broadcast

    def handle_auto_switch(self, message):
        broadcast = True

        if message[1] == 'A':
            broadcast = False
            resp = str(self.auto_switch_mode)
        else:
            setting = int(message[1])

            if 0 < setting < 3:
                self.auto_switch_mode = setting
                resp = 'Ausw{}'.format(setting)
            else:
                resp = 'E13'
                broadcast = False

        return resp, broadcast

    def handle_input_status(self, message):
        return '{} {} {} {} {} {}*{}'.format(*self.connection_state), False

    def handle_verbose_mode(self, message):
        """
        Note: we accept and respond to this command because our driver checks for it on initial_connection, however
        since we cannot handle individual sessions at this moment we act like the device is always in verbose mode. I am
        of course assuming here that verbose mode is a per-connection thing, I may be incorrect about that.
        """
        if message[1].isnumeric():
            # TODO: should we broadcast this?
            # TODO: once we figure out how exactly this works (per-connection or for all connections) actually store
            # the state.
            return 'Vrb{}'.format(message[1]), True
        else:
            # TODO: when we store verbose mode state return it here.
            return '1', False

    def handle_message(self, message):
        self.logger.info('Message received: {}'.format(message))

        if 'AUSW' in message:
            resp = self.handle_auto_switch(message)
        elif '!' in message:
            resp = self.handle_input(message)
        elif '0LS' in message:
            resp = self.handle_input_status(message)
        elif 'CV' in message:
            resp = self.handle_verbose_mode(message)
        else:
            resp = 'E10', False

        self.logger.info('Sending response: "{}"'.format(resp[0]))

        return resp

    def start(self):
        super().start()
        self.logger.info('ExtronMps601Emulator v{} started on port {}'.format(__version__, self.port))

        if self.debug:
            self.logger.debug('Debug mode enabled')

    def set_connection_status(self, num: int, status: bool):
        """
        Alters the connection status of an input or the output and braodcasts the message to all connected clients.
        :param num: 0-6, if it is 0-5 it is input 1-6, if it is 6 it is the output
        :param status: True to set as connected, False to set as disconnected
        :return: None
        """
        self.logger.debug('Set Connection Status: {}, {}'.format(num, int(status)))
        self.connection_state[num] = int(status)
        # TODO: Determine if connection status actually gets broadcast
        # TODO: If it it does broadcast determine if this is the appropriate format to broadcast in
        message = 'Sig {} {} {} {} {} {}*{}'.format(*self.connection_state)
        self.logger.debug(message)
        self.transport.broadcast_message(message)

    def set_input(self, num):
        self.active_input = num
        self.transport.broadcast_message('In{} All'.format(self.active_input))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Start a TCP server.')
    parser.add_argument('port', help='The port to bind the TCP service to.')
    parser.add_argument('--debug', action='store_true', default=False, help='Enables debug')
    args = parser.parse_args()
    em = ExtronMps601Emulator(int(args.port), debug=args.debug)
    em.start()

    while True:
        # TODO: write documentation for supported commands, write help command
        user_input = input('Enter Command:')
        options = user_input.split(' ')

        if options[0] == 'c':
            # Enable or disable the input or output selected.
            if len(options) != 3:
                print('The connection command only takes two args')
                continue

            io = int(options[1])
            status = bool(int(options[2]))
            em.set_connection_status(io, status)
        elif options[0] == 's':
            if len(options) > 2:
                print('The switch command only takes 1 arg')
                continue

            inpt = int(options[1])

            if inpt < 1 or inpt > 6:
                print('The switch command only accepts values 1-6')
                continue

            em.set_input(inpt)
