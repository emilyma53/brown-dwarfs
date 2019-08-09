# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Base configuration management."""

# Standard library imports
import os
import os.path as osp

# Local imports
from navigator_updater.utils import encoding

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
