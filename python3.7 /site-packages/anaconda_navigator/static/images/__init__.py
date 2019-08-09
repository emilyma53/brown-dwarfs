# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""
This folder contains image files bundled with Anaconda Navigator package.

This folder is defined as a python module so that some convenience global
variables can be defined.
"""

# yapf: disable

from __future__ import absolute_import, division, print_function

# Standard library imports
import os.path as osp


# yapf: enable

IMAGE_PATH = osp.dirname(osp.realpath(__file__))
LOGO_PATH = osp.join(IMAGE_PATH, 'logos')

# --- Anaconda Logo
# -----------------------------------------------------------------------------
ANACONDA_LOGO = osp.join(IMAGE_PATH, 'anaconda-logo.svg')
ANACONDA_LOGO_WHITE = osp.join(IMAGE_PATH, 'anaconda-logo-white.svg')
ANACONDA_NAVIGATOR_LOGO = osp.join(IMAGE_PATH, 'anaconda-navigator-logo.svg')
ANACONDA_ICON_256_PATH = osp.join(IMAGE_PATH, 'anaconda-icon-256x256.png')

# TODO: Check copyright on this image
VIDEO_ICON_PATH = osp.join(IMAGE_PATH, 'default-content.png')

# --- Application icons
# -----------------------------------------------------------------------------
GLUEVIZ_ICON_1024_PATH = osp.join(IMAGE_PATH, 'glueviz-icon-1024x1024.png')
NOTEBOOK_ICON_1024_PATH = osp.join(IMAGE_PATH, 'jupyter-icon-1024x1024.png')
ORANGE_ICON_1024_PATH = osp.join(IMAGE_PATH, 'orange-icon-1024x1024.png')
QTCONSOLE_ICON_1024_PATH = osp.join(IMAGE_PATH, 'qtconsole-icon-1024x1024.png')
SPYDER_ICON_1024_PATH = osp.join(IMAGE_PATH, 'spyder-icon-1024x1024.png')
RODEO_ICON_1024_PATH = osp.join(IMAGE_PATH, 'rodeo-icon-1024x1024.png')
VEUSZ_ICON_1024_PATH = osp.join(IMAGE_PATH, 'veusz-icon-1024x1024.png')
RSTUDIO_ICON_1024_PATH = osp.join(IMAGE_PATH, 'rstudio-icon-1024x1024.png')
JUPYTERLAB_ICON_1024_PATH = osp.join(
    IMAGE_PATH, 'jupyterlab-icon-1024x1024.png'
)
VSCODE_ICON_1024_PATH = osp.join(IMAGE_PATH, 'vscode-icon-1024x1024.png')
QTCREATOR_ICON_1024_PATH = osp.join(IMAGE_PATH, 'qtcreator-icon-1024x1024.png')

# --- Spinners
# -----------------------------------------------------------------------------
# http://preloaders.net/en/circular
SPINNER_16_PATH = osp.join(IMAGE_PATH, 'spinner-16x16.gif')
SPINNER_32_PATH = osp.join(IMAGE_PATH, 'spinner-32x32.gif')
SPINNER_GREEN_16_PATH = osp.join(IMAGE_PATH, 'spinner-green-16x16.gif')
SPINNER_WHITE_16_PATH = osp.join(IMAGE_PATH, 'spinner-white-16x16.gif')

# Conda Package Manager Table icons
# -----------------------------------------------------------------------------
MANAGER_INSTALLED = osp.join(
    IMAGE_PATH, 'icons', 'check-box-checked-active.svg'
)
MANAGER_NOT_INSTALLED = osp.join(IMAGE_PATH, 'icons', 'check-box-blank.svg')
MANAGER_ADD = osp.join(IMAGE_PATH, 'icons', 'mark-install.svg')
MANAGER_REMOVE = osp.join(IMAGE_PATH, 'icons', 'mark-remove.svg')
MANAGER_DOWNGRADE = osp.join(IMAGE_PATH, 'icons', 'mark-downgrade.svg')
MANAGER_UPGRADE = osp.join(IMAGE_PATH, 'icons', 'mark-upgrade.svg')
MANAGER_UPGRADE_ARROW = osp.join(IMAGE_PATH, 'icons', 'update-app-active.svg')
MANAGER_SPACER = osp.join(IMAGE_PATH, 'conda-manager-spacer.svg')
WARNING_ICON = osp.join(IMAGE_PATH, 'icons', 'warning-active.svg')
INFO_ICON = osp.join(IMAGE_PATH, 'icons', 'info-active.svg')
PYTHON_LOGO = osp.join(IMAGE_PATH, 'python-logo.svg')
