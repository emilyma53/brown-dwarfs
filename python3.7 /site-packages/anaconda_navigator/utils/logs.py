# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Logger utilties."""

# yapf: disable

# Standard library imports
import json
import logging.handlers
import os

# Local imports
from anaconda_navigator.config import (LOG_FILENAME, LOG_FOLDER,
                                       MAX_LOG_FILE_SIZE)


# yapf: disable

# Constants
JSON_SEPARATOR = '\x00'

# Main logger instance
logger = logging.getLogger('navigator')


class ContextFilter(logging.Filter):
    """This is a filter that replaces `\` by `/` for json parsing."""

    @staticmethod
    def filter(record):
        """On windows make sure that slashes do not interfere with json."""
        # print([i for i in dir(record) if not i.startswith('_')])
        if isinstance(record.msg, dict):
            for k, v in record.msg.items():
                if isinstance(v, str):
                    record.msg[k] = v.replace('\\', '/')
        elif record.msg and isinstance(record.msg, str):
            record.msg = record.msg.replace('\\', '/')
            record.msg = repr(record.msg).replace('"', "'")

            if record.msg[0] == "'":
                record.msg = record.msg[1:]
            if record.msg[-1] == "'":
                record.msg = record.msg[:-1]

        if record.pathname:
            record.pathname = record.pathname.replace('\\', '/')

        return True


def setup_logger(
    log_level=logging.WARNING,
    log_folder=LOG_FOLDER,
    log_filename=LOG_FILENAME,
    log_file_size=MAX_LOG_FILE_SIZE,
    log_backup_count=5
):
    """Setup, create, and set logger."""
    global logger

    if not os.path.isdir(log_folder):
        os.makedirs(log_folder)

    log_file_path = os.path.join(log_folder, log_filename)

    # Reset extra loggers
    root_logger = logging.getLogger()
    root_logger.handlers = []

    # Setup logger for navigator application and reset handlers
    logger.setLevel(logging.DEBUG)
    logger.handlers = []

    # Create file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path,
        maxBytes=log_file_size,
        backupCount=log_backup_count,
    )

    file_handler.setLevel(log_level)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # Create formatters
    file_formatter = logging.Formatter(
        '{'
        '"time": "%(asctime)s", '
        '"level": "%(levelname)s", '
        '"module": "%(module)s", '
        '"method": "%(funcName)s", '
        '"line": %(lineno)d, '
        '"path": "%(pathname)s", '
        '"message": "%(message)s"'
        '}' + JSON_SEPARATOR,
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s %(module)s.%(funcName)s:%(lineno)d\n'
        '%(message)s\n',
    )

    # Set formatters
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)

    # Add filters
    filt = ContextFilter()
    file_handler.addFilter(filt)
    console_handler.addFilter(filt)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.info('Setting up logger')


def log_files(log_folder=LOG_FOLDER, log_filename=LOG_FILENAME):
    """
    Return all available log files located inside the logs folder.

    Files starting with a `.` are ignored as well as files not including the
    `log_filename` as part of the name.
    """
    paths = []
    if os.path.isdir(log_folder):
        log_files = os.listdir(log_folder)
        for log_file in sorted(log_files):
            log_file_path = os.path.join(log_folder, log_file)
            if (os.path.isfile(log_file_path) and log_filename in log_file and
                    not log_file.startswith('.')):
                paths.append(log_file_path)
    return paths


def clean_logs(log_folder=LOG_FOLDER):
    """Remove logs in old plain text format."""
    for path in log_files(log_folder):
        if os.path.isfile(path):
            with open(path, 'r') as f:
                data = f.read()

            new_lines = []
            lines = data.split('\n')
            for line in lines:
                if JSON_SEPARATOR in line:
                    new_lines.append(line)

            new_separator = JSON_SEPARATOR + '\n'
            with open(path, 'w') as f:
                f.write(new_separator.join(new_lines))


def load_log(log_file_path):
    """Load log file and return list of items."""
    if os.path.isfile(log_file_path):
        with open(log_file_path, 'r') as f:
            data = f.read()
        json_lines = data.split(JSON_SEPARATOR)

    # Remove empty lines
    json_lines = [line for line in json_lines if line and line != '\n']

    data = []
    for i, line in enumerate(json_lines):
        try:
            data.append(json.loads(line))
        except Exception as e:
            logger.warning('Line {0}. Exception - {1}'.format(i, str(e)))
    return data
