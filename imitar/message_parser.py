# Copyright 2015 jydo inc. All rights reserved.
from abc import abstractmethod
from abc import ABCMeta


class MessageParser(metaclass=ABCMeta):
    @abstractmethod
    def process_buffer(self, buffer) -> tuple:
        """
        This method is in charge of taking a buffer and chunking it into multiple messages (if there are multiples) and
        returning the messages and new buffer.

        return: tuple(messages, buffer)
        """
        pass


class CharacterMessageParser(MessageParser):
    def __init__(self, delimiter, encoding=None):
        """
        Chunks buffers based on a character delimiter.
        """
        if isinstance(delimiter, (bytes, bytearray)):
            self.delimiter = delimiter
        elif encoding is not None:
            self.delimiter = delimiter.encode(encoding)
        else:
            raise ValueError('Delimiter must be a bytes or bytearray object if no encoding is provided')

        self.encoding = encoding

    def process_buffer(self, buffer: bytearray):
        messages = []
        encoded_messages = buffer.split(self.delimiter)
        # If the last character received was a delimiter then the last message is an empty bytearray, otherwise it's an
        # incomplete message, either way we don't want it in the messages array.
        new_buffer = encoded_messages.pop(-1)

        if self.encoding is not None:
            for message in encoded_messages:
                messages.append(message.decode(self.encoding))
        else:
            messages = encoded_messages

        return messages, new_buffer


class VariableLengthMessageParser(MessageParser):
    def __init__(self, header, length_index=1, footer_length=0):
        """
        Parses a stream that contains length delimited messages. Note this parser assumes the length

        :param header: The byte or bytes that indicate the beginning of a message
        :param length_index: The index of the length byte relative to the header, typically, but not always, the first
        byte after the header.
        :param footer_length: The size of the footer if the length byte does not count it. Most protocols don't need
        this, but for example the Samsung MDC protocol does.
        """
        if header is not None and not isinstance(header, (bytes, bytearray)):
            raise ValueError('header must be None, bytes, or bytearray')

        self.header = header
        self.length_index = length_index
        self.footer_length = footer_length

    def process_buffer(self, buffer: bytearray):
        messages = []

        while True:
            header_index = 0

            if self.header is not None:
                header_index = buffer.find(self.header)

            if header_index < 0:
                # If we don't have the header yet return.
                break

            # Remove anything before the header, it's garbage.
            buffer = buffer[header_index:]

            if self.length_index >= len(buffer):
                # If we haven't received the length bit yet return
                break

            # Accessing a byte via an index returns the integer value
            length = buffer[self.length_index] + self.footer_length
            start_index = self.length_index + 1
            end_index = start_index + length

            if end_index > len(buffer):
                # If we don't have the required length then we don't have a complete message yet, return.
                break

            messages.append(buffer[start_index:end_index])
            buffer = buffer[end_index:]

        return messages, buffer


class FixedLengthMessageParser(MessageParser):
    def __init__(self, header, length):
        self.header = header
        self.length = length

    def process_buffer(self, buffer):
        messages = []
        header_index = 0

        while len(buffer) >= self.length:
            if self.header is not None:
                header_index = buffer.find(self.header)

            if header_index < 0:
                break

            # Remove anything before the header, it's garbage.
            buffer = buffer[header_index:]

            if len(buffer) < self.length:
                break

            messages.append(buffer[:self.length])
            buffer = buffer[self.length:]

        return messages, buffer
