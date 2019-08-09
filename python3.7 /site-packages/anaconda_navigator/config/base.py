# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Base configuration management."""

# yapf: disable

# Standard library imports
import os
import os.path as osp
import sys

# Local imports
from anaconda_navigator.utils import encoding


# yapf: enable

# -----------------------------------------------------------------------------
# --- Configuration paths
# -----------------------------------------------------------------------------
SUBFOLDER = os.path.join('.anaconda', 'navigator')


def get_home_dir():
    """Return user home directory."""
    try:
        # expanduser() returns a raw byte string which needs to be
        # decoded with the codec that the OS is using to represent file paths.
        path = encoding.to_unicode_from_fs(osp.expanduser('~'))
    except Exception:
        path = ''
    for env_var in ('HOME', 'USERPROFILE', 'TMP'):
        if osp.isdir(path):
            break
        # os.environ.get() returns a raw byte string which needs to be
        # decoded with the codec that the OS is using to represent environment
        # variables.
        path = encoding.to_unicode_from_fs(os.environ.get(env_var, ''))
    if path:
        return path
    else:
        raise RuntimeError('Please define environment variable $HOME')


def get_conf_path(filename=None):
    """Return absolute path for configuration file with specified filename."""
    conf_dir = osp.join(get_home_dir(), SUBFOLDER)
    if not osp.isdir(conf_dir):
        os.makedirs(conf_dir)
    if filename is None:
        return conf_dir
    else:
        return osp.join(conf_dir, filename)


def is_ubuntu():
    """Detect if we are running in an Ubuntu-based distribution."""
    if sys.platform.startswith('linux') and os.path.isfile('/etc/lsb-release'):
        with open('/etc/lsb-release', 'r') as f:
            release_info = f.read()

        if 'ubuntu' in release_info.lower():
            return True
        else:
            return False
    else:
        return False


def is_gtk_desktop():
    """Detect if we are running in a Gtk-based desktop."""
    if sys.platform.startswith('linux'):
        xdg_desktop = os.environ.get('XDG_CURRENT_DESKTOP', '')
        if xdg_desktop:
            gtk_desktops = ['Unity', 'GNOME', 'XFCE']
            if any([xdg_desktop.startswith(d) for d in gtk_desktops]):
                return True
            else:
                return False
        else:
            return False
    else:
        return False
