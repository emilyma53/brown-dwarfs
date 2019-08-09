# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""
This folder contains data files bundled with Anaconda Navigator package.

This folder is defined as a python module so that some convenience global
variables can be defined.
"""

# yapf: disable

from __future__ import absolute_import, division, print_function

# Standard library imports
import os.path as osp

# Local imports
from anaconda_navigator.config import CONF_PATH, METADATA_PATH


# yapf: enable

DATA_PATH = osp.dirname(osp.realpath(__file__))
CONTENT_INFO_PATH = osp.join(CONF_PATH, 'videos.json')
LINKS_INFO_PATH = osp.join(DATA_PATH, 'links.json')
CONF_METADATA_PATH = osp.join(METADATA_PATH, 'metadata.json')
BUNDLE_METADATA_COMP_PATH = osp.join(DATA_PATH, 'metadata.json.bz2')
