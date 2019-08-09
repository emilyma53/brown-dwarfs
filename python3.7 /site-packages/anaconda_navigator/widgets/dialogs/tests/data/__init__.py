# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Tests for license dialog."""

# yapf: disable

# Standard library imports
import os


# yapf: enable

HERE = os.path.dirname(os.path.abspath(__file__))
LIC_EXPIRED_NAME = 'license_bundle_20160829215841_expired.txt'
LIC_INVALID_NAME = 'license_bundle_20160829215841_invalid.txt'
EXPIRED_LICENSE_PATH = os.path.join(HERE, LIC_EXPIRED_NAME)
INVALID_LICENSE_PATH = os.path.join(HERE, LIC_INVALID_NAME)
