# Copyright 2015 jydo inc. All rights reserved.
import sys
from logging import getLogger, StreamHandler
from threading import Thread

from imitar.emulator import Emulator
from imitar.message_parser import CharacterMessageParser

__version__ = '1.0.0'
_logger = getLogger('fake_tv_server')
_logger.addHandler(StreamHandler(stream=sys.stdout))
DELIMITER = '\r\n'
ENCODING = 'ascii'


def run_later(fn, seconds):
    def later():
        time.sleep(seconds)
        fn()

    Thread(target=later, daemon=True).start()


class FakeTvEmulator(Emulator):
    """
    This class implements a protocol that acts like a networked TV. This is a network service that communicates over
    TCP.
    """
    welcome_message = 'FakeTvServer v{}'.format(__version__)
    logger = _logger
    message_parser = CharacterMessageParser(DELIMITER, ENCODING)

    def __init__(self, port, debug=False):
        super().__init__(port, self.message_parser, debug=debug)
        self.power = '0'
        self.volume = 0
        self.mute = '0'
        self.input = 'HDMI_1'
        self.available_inputs = {'HDMI_1', 'HDMI_2', 'VGA', 'DVI'}
        self.powering_off = False
        self.command_map = {
            'POWR': self.handle_power,
            'VOLM': self.handle_volume,
            'MUTE': self.handle_mute,
            'INPT': self.handle_input
        }

    def power_off_callback(self):
        self.powering_off = False
        self.transport.close_all_clients()

    def handle_power(self, value):
        broadcast = False

        if value not in ['?', '0', '1']:
            return 'ERR', broadcast

        if value == '0' or value == '1':
            broadcast = True
            last_value = self.power
            self.power = value

            if last_value == '1' and value == '0':
                # If the device changes from power on to power off, then we want to wait three seconds to emulate power
                # off and then broadcast to all clients that the TV is powered on. Then close all connected clients via
                # power_off_callback
                msg = 'POWR 0'
                time.sleep(3)
                self.powering_off = True
                self.logger.debug('Broadcasting {}'.format(msg))
                self.transport.broadcast_message(msg)
                run_later(self.power_off_callback, 3)

                return None, False

        return 'POWR {}'.format(self.power), broadcast

    def handle_volume(self, value):
        broadcast = False

        if value != '?':
            broadcast = True

            try:
                value = int(value, 10)
            except ValueError:
                return 'ERR', False

            if value < 0 or value > 100:
                return 'ERR', False

            self.volume = value

        return 'VOLM {}'.format(self.volume), broadcast

    def handle_mute(self, value):
        broadcast = False

        if value != '?':
            broadcast = True

            if value == '0' or value == '1':
                self.mute = value
            else:
                return 'ERR', False

        return 'MUTE {}'.format(self.mute), broadcast

    def handle_input(self, value):
        broadcast = False

        if value != '?':
            broadcast = True

            if value not in self.available_inputs:
                return 'ERR', False

            self.input = value

        return 'INPT {}'.format(self.input), broadcast

    def handle_message(self, message):
        self.logger.info('Message received: "{}"'.format(message))

        if self.powering_off:
            # Discard all incoming messages until after 3 seconds after power on.
            return None

        try:
            cmd, value = message.split(' ')
        except ValueError:
            cmd = message
            value = ''

        handler = self.command_map.get(cmd)
        resp = ('ERR', False)

        if handler is not None:
            resp = self.command_map[cmd](value)

        self.logger.info('Sending response: "{}"'.format(resp[0]))

        return resp

    def start(self):
        super().start()
        self.logger.info('FakeTvServer v{} started on port {}'.format(__version__, self.port))

        if self.debug:
            self.logger.debug('Debug mode enabled')


if __name__ == '__main__':
    import argparse
    import time

    parser = argparse.ArgumentParser(description='Start a TCP server.')
    parser.add_argument('port', type=int, help='The port to bind the TCP service to.')
    parser.add_argument('--debug', action='store_true', default=False, help='Enables debug')
    args = parser.parse_args()
    tv = FakeTvEmulator(args.port, debug=args.debug)
    tv.start()

    try:
        while True:
            time.sleep(1)
    except (Exception, KeyboardInterrupt):
        tv.shutdown(None, None)
