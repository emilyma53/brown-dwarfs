# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2017 Continuum Analytics, Inc.
# Copyright (c) 2010 Preston Landers (Released under the Python 2.6.5 license)
# Copyright (c) 2008-2011 by Enthought, Inc.
# All rights reserved.
#
# Licensed under the terms of the BSD 3-clause License (See LICENSE.txt)
# -----------------------------------------------------------------------------
"""
See: http://stackoverflow.com/a/19719292/1170370 on 20160407 MCS.
"""

# yapf: disable

from __future__ import print_function, unicode_literals

# Standard library imports
import ctypes
import enum
import os
import sys
import traceback


# yapf: enable


def is_user_admin():
    if os.name == 'nt':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            traceback.print_exc()
            # print("Admin check failed, assuming not an admin.")
            return False
    elif os.name == 'posix':
        # Check for root on Posix
        return os.getuid() == 0
    else:
        raise RuntimeError(
            "Unsupported operating system for this module: %s" % (os.name, )
        )


class SW(enum.IntEnum):
    HIDE = 0
    MAXIMIZE = 3
    MINIMIZE = 6
    RESTORE = 9
    SHOW = 5
    SHOWDEFAULT = 10
    SHOWMAXIMIZED = 3
    SHOWMINIMIZED = 2
    SHOWMINNOACTIVE = 7
    SHOWNA = 8
    SHOWNOACTIVATE = 4
    SHOWNORMAL = 1


class ERROR(enum.IntEnum):
    ZERO = 0
    FILE_NOT_FOUND = 2
    PATH_NOT_FOUND = 3
    BAD_FORMAT = 11
    ACCESS_DENIED = 5
    ASSOC_INCOMPLETE = 27
    DDE_BUSY = 30
    DDE_FAIL = 29
    DDE_TIMEOUT = 28
    DLL_NOT_FOUND = 32
    NO_ASSOC = 31
    OOM = 8
    SHARE = 26


def run_as_admin(cmd_line):
    """
    msdn.microsoft.com/en-us/library/windows/desktop/bb762153(v=vs.85).aspx
    """
    params = " ".join(['"%s"' % (x, ) for x in cmd_line[1:]])
    hinstance = ctypes.windll.shell32.ShellExecuteW(
        None, 'runas', cmd_line[0], params, None, SW.HIDE
    )

    if hinstance <= 32:
        code = None
        # RuntimeError(ERROR(hinstance))
    else:
        code = hinstance

    return code


if __name__ == '__main__':
    is_user_admin = is_user_admin()
    print('userIsAdmin = %d' % (is_user_admin))
    if not is_user_admin:
        run_as_admin([sys.executable] + sys.argv, wait=True)
