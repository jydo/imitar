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
        super().__init__(port, self.message_parser, debug=debug)
        self.connection_state = [1, 1, 1, 1, 1, 1, 1]
        self.active_input = 1
        self.auto_switch_mode = 0

    def handle_input(self, message):
        broadcast = False

        if message[0].isnumeric() and self.auto_switch_mode == 0:
            active_input = int(message[0])
            self.active_input = active_input
            resp = 'In{} All'.format(active_input)
            broadcast = True
        elif message[0].isnumeric():
            # Return an error if auto-switch is enabled and the user tries to switch the input.
            resp = 'E06'
        else:
            resp = str(self.active_input)

        return resp, broadcast

    def handle_auto_switch(self, message):
        if message[1] == 'A':
            return str(self.auto_switch_mode), False

        setting = int(message[1])

        if 0 < setting < 3:
            self.auto_switch_mode = setting
            resp = 'Ausw{}'.format(setting)
            broadcast = True
        else:
            resp = 'E13'
            broadcast = False

        return resp, broadcast

    def handle_input_status(self):
        return '{} {} {} {} {} {}*{}'.format(*self.connection_state), False

    def handle_verbose_mode(self, message):
        if message[1].isnumeric():
            # TODO: This is the correct response, but the manual isn't clear on what verbose mode means. The only device
            # that I briefly had access to was in verbose mode, so this emulator essentially always assumes verbose mode
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
            resp = self.handle_input_status()
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
        :param num: 0-6, if it is 0-5 it is input 1-6, 6 is the output
        :param status: True to set as connected, False to set as disconnected
        :return: None
        """
        self.logger.debug('Set Connection Status: {}, {}'.format(num, int(status)))
        self.connection_state[num] = int(status)
        input_status, _ = self.handle_input_status()
        message = 'Sig ' + input_status
        self.logger.debug(message)
        self.transport.broadcast_message(message)

    def set_input(self, num):
        self.active_input = num
        self.transport.broadcast_message('In{} All'.format(self.active_input))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Start a TCP server.')
    parser.add_argument('port', type=int, help='The port to bind the TCP service to.')
    parser.add_argument('--debug', action='store_true', default=False, help='Enables debug')
    args = parser.parse_args()
    em = ExtronMps601Emulator(args.port, debug=args.debug)
    em.start()

    while True:
        # TODO: write documentation for supported commands, write help command
        user_input = input('Enter Command:')
        options = user_input.split(' ')

        if options[0] == 'c':
            # Enable or disable the input or output selected.
            if len(options) != 3 or options[1] == '?':
                print('The command must be in the format of "c [input or output] [connected status]"')
                print('0-5 are input ports, 6 is the output port')
                print('The connected status may be 0 for disconnected or 1 for connected')
                print('Example: "c 1 0" will set the 2nd port to the disconnected status.')
                continue

            io = int(options[1])
            status = bool(int(options[2]))
            em.set_connection_status(io, status)
        elif options[0] == 's':
            if len(options) != 2 or options[1] == '?':
                print('The command must be in the format of "s [input number]"')
                print('0-5 are valid input numbers.')
                print('Example: "s 1" will switch the 2nd input to the output port')
                continue

            inpt = int(options[1])

            if inpt < 1 or inpt > 6:
                print('The switch command only accepts values 1-6')
                continue

            em.set_input(inpt)
