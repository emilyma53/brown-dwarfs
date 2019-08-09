#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Application entry point."""

# yapf: disable

# Standard library imports
import os
import shutil
import sys

# Local imports
from anaconda_navigator import __version__
from anaconda_navigator.app.cli import parse_arguments
from anaconda_navigator.exceptions import exception_handler
from anaconda_navigator.utils.conda import is_conda_available


# yapf: enable


def main():  # pragma: no cover
    """Main application entry point."""
    # Check if conda is available
    if not is_conda_available():
        path = os.path.abspath(os.path.dirname(sys.argv[0]))
        # print(path, len(sys.argv))
        msg = '''#
# Please activate the conda root enviroment properly before running the
# `anaconda-navigator` command.
'''
        win_msg = '''#
# To activate the environment please open a Windows Command Prompt and run:
#
#   {0}\\activate root
'''.format(path)

        unix_msg = '''#
# To activate the environment please open a terminal and run:
#
#   source {0}/activate root
'''.format(path)

        more_info = '''#
# For more information please see the documentation at:
#
#   https://docs.anaconda.com/anaconda/navigator/
#'''
        if os.name == 'nt':
            print_msg = '{}{}{}'.format(msg, win_msg, more_info)
        else:
            print_msg = '{}{}{}'.format(msg, unix_msg, more_info)

        print(print_msg)

        return 1

    # Parse CLI arguments
    options = parse_arguments()

    # Return information on version
    if options.version:
        print(__version__)
        sys.exit(0)

    # Reset Navigator conifg
    if options.reset:
        print('\nAnaconda Navigator configuration reset...\n\n')
        from anaconda_navigator.config import CONF_PATH
        if os.path.isdir(CONF_PATH):
            try:
                shutil.rmtree(CONF_PATH)
                print('Anaconda Navigator configuration reset successful!\n')
                sys.exit(0)
            except Exception as e:
                print('Anaconda Navigator configuration reset failed!!!\n')
                print(e)
                sys.exit(1)

    if options.removelock:
        print('\nRemoving Anaconda Navigator lock...\n\n')
        from anaconda_navigator.utils.misc import remove_lock, remove_pid
        lock = remove_lock()
        pid = remove_pid()
        if lock and pid:
            print('Anaconda Navigator lock removal successful!\n')
            sys.exit(0)
        else:
            print('Anaconda Navigator lock removal failed!!!\n')
            sys.exit(1)

    # Clean old style logs
    from anaconda_navigator.utils.logs import clean_logs
    clean_logs()

    # Import app
    from anaconda_navigator.app.start import start_app
    return exception_handler(start_app, options)


if __name__ == '__main__':  # pragma: no cover
    main()
