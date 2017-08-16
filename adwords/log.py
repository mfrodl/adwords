# -*- coding: utf-8 -*-

import config
import logging

class ConsoleFormatter(logging.Formatter):
    formats = {
        logging.ERROR: '[ \033[91m%(levelname)s\033[0m  ] %(message)s',
        logging.WARNING: '[  \033[93mWARN\033[0m  ] %(message)s',
        logging.INFO: '[  \033[94m%(levelname)s\033[0m  ] %(message)s',
        logging.DEBUG: '[ \033[97m%(levelname)s\033[0m  ] %(message)s',
        None: '[ %(levelname)s ] %(message)s',
    }

    def format(self, record):
        self._fmt = self.formats.get(record.levelno, self.formats[None])
        return logging.Formatter.format(self, record)

def configure_logging(level=logging.DEBUG):
    """ Set appropriate log level """
    for logger in logging.Logger.manager.loggerDict:
        logging.getLogger(logger).setLevel(logging.WARN)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    plain_formatter = logging.Formatter('[ %(levelname)s ] %(message)s')
    console_formatter = ConsoleFormatter()

    stream_handler = logging.StreamHandler()
    if stream_handler.stream.isatty():
        stream_handler.setFormatter(console_formatter)
    else:
        stream_handler.setFormatter(plain_formatter)
    stream_handler.setLevel(level)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(config.LOG_FILE)
    file_handler.setFormatter(plain_formatter)
    file_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
