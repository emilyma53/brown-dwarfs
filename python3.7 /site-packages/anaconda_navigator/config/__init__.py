# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""
Module in charge of the configuration settings.

It uses a modified version of Python's configuration parser.
"""

# yapf: disable

# Standard library imports
from subprocess import PIPE
import os
import platform
import subprocess
import sys

# Local imports
from anaconda_navigator import __version__
from anaconda_navigator.config.base import (get_conf_path, get_home_dir,
                                            is_gtk_desktop, is_ubuntu)
from anaconda_navigator.config.main import CONF


# yapf: enable

# FLAGS
CONF
TEST_CI = os.environ.get('TEST_CI', False)
MAC = sys.platform == 'darwin'

if MAC:
    MAC_VERSION = platform.mac_ver()[0]
    MAC_VERSION_INFO = []
    for v in MAC_VERSION.split('.'):
        value = ver = int(v) if v.isdigit else v
        MAC_VERSION_INFO.append(value)
    MAC_VERSION_INFO = tuple(MAC_VERSION_INFO)
else:
    MAC_VERSION = ''
    MAC_VERSION_INFO = tuple()

WIN = os.name == 'nt'
try:
    WIN7 = platform.platform().lower().startswith('windows-7')
except Exception:
    WIN7 = False

LINUX = sys.platform.startswith('linux')
LINUX_DEB = False
LINUX_RPM = False
LINUX_DNF = False

if LINUX:
    try:
        p = subprocess.check_call(
            ['dpkg', '--version'], stdout=PIPE, stderr=PIPE
        )
        LINUX_DEB = True
    except Exception as e:
        LINUX_DEB = False
        # print(e)

    try:
        p = subprocess.check_call(
            ['rpm', '--version'], stdout=PIPE, stderr=PIPE
        )
        LINUX_RPM = True
    except Exception as e:
        LINUX_RPM = False
        # print(e)

    try:
        p = subprocess.check_call(
            ['dnf', '--version'], stdout=PIPE, stderr=PIPE
        )
        LINUX_DNF = True
    except Exception as e:
        LINUX_DNF = False
        # print(e)

    # print('is DEB', LINUX_DEB)
    # print('is RPM', LINUX_RPM)

UBUNTU = is_ubuntu()
GTK = is_gtk_desktop()
DEV = 'dev' in __version__
BITS = 8 * tuple.__itemsize__
BITS_64 = BITS == 64
BITS_32 = BITS == 32
OS_64_BIT = platform.machine().endswith('64')

# Paths
HOME_PATH = get_home_dir()
CONF_PATH = get_conf_path()
LAUNCH_SCRIPTS_PATH = os.path.join(CONF_PATH, 'scripts')
CONTENT_PATH = os.path.join(CONF_PATH, 'content')
CONTENT_JSON_PATH = os.path.join(CONTENT_PATH, 'content.json')
IMAGE_ICON_SIZE = (256, 256)
IMAGE_DATA_PATH = os.path.join(CONF_PATH, 'images')
CHANNELS_PATH = os.path.join(CONF_PATH, 'channels')
METADATA_PATH = os.path.join(CONF_PATH, 'metadata')
DEFAULT_PROJECTS_PATH = os.path.join(HOME_PATH, 'AnacondaProjects')
LOCKFILE = os.path.join(CONF_PATH, 'navigator.lock')
PIDFILE = os.path.join(CONF_PATH, 'navigator.pid')
DEFAULT_BRAND = 'Anaconda Cloud'
GLOBAL_VSCODE_APP = 'vscode'

# License management
LICENSE_PATH = '__filepath__'
REMOVED_LICENSE_PATH = '.removed_licenses'
# Other license like cluster dont really have a meaning for a dekstop user
# using navigator
VALID_PRODUCT_LICENSES = [
    'accelerate',
    'Anaconda Enterprise Notebooks',
    'Anaconda Enterprise Repository',
    'Anaconda Repository Enterprise',
    'Anaconda Enterprise',
    'Wakari',
    'iopro',
    'mkl-optimizations',
]
PACKAGES_WITH_LICENSE = [
    'anaconda-fusion',
    'anaconda-mosaic',
]
LICENSE_NAME_FOR_PACKAGE = {
    'anaconda-fusion': [
        'Anaconda Enterprise Notebooks',
        'Anaconda Enterprise Repository',
        'Anaconda Repository Enterprise',
        'Anaconda Enterprise',
        'Wakari',
        'Wakari Enterprise',
    ],
}

VALID_DEV_TOOLS = ['notebook', 'qtconsole', 'spyder']
LOG_FOLDER = os.path.join(CONF_PATH, 'logs')
LOG_FILENAME = 'navigator.log'

MAX_LOG_FILE_SIZE = 2 * 1024 * 1024
