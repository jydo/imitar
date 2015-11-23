# Copyright 2015 jydo inc. All rights reserved.
from imitar.message_parser import CharacterMessageParser, FixedLengthMessageParser, VariableLengthMessageParser


def check_message_parser(mp, incoming, expected_messages, expected_buffer):
    # Emulate a stream of bytes coming in, make sure the message parser can handle incomplete messages
    for i in range(1, len(incoming) + 1):
        partial_message = incoming[0:i]
        mp.process_buffer(partial_message)

    messages, buffer = mp.process_buffer(incoming)

    assert messages == expected_messages
    assert buffer == expected_buffer


def test_character_message_parser():
    incoming = bytearray(b'MESSAGE ONE\r\nMESSAGE TWO\r\nMESS')
    mp_with_encoding = CharacterMessageParser('\r\n', 'ascii')
    mp_without_encoding = CharacterMessageParser(b'\r\n')

    check_message_parser(mp_with_encoding, incoming, ['MESSAGE ONE', 'MESSAGE TWO'], b'MESS')
    check_message_parser(mp_without_encoding, incoming, [b'MESSAGE ONE', b'MESSAGE TWO'], b'MESS')


def test_fixed_length_message_parser():
    incoming = bytearray(b'\xaa\xff\xff\xfe\xaa\x1b\x2b\x3b\xaa')
    mp_no_header = FixedLengthMessageParser(None, 3)
    no_header_messages = [bytearray(b'\xaa\xff\xff'), bytearray(b'\xfe\xaa\x1b'), bytearray(b'\x2b\x3b\xaa')]
    mp_with_header = FixedLengthMessageParser(b'\xaa', 3)
    with_header_messages = [bytearray(b'\xaa\xff\xff'), bytearray(b'\xaa\x1b\x2b')]

    check_message_parser(mp_no_header, incoming, no_header_messages, b'')
    check_message_parser(mp_with_header, incoming, with_header_messages, b'\x3b\xaa')


def test_variable_length_message_parser():
    # This is an example response from a Samsung MDC device, note there is 1 full message and one partial message
    incoming = bytearray(b'\xaa\xff\x00\x03\x41\x12\x32\x00\xaa\xff\x00')
    mp = VariableLengthMessageParser(b'\xaa', 3, 1)

    check_message_parser(mp, incoming, [b'\x41\x12\x32\x00'], b'\xaa\xff\x00')
