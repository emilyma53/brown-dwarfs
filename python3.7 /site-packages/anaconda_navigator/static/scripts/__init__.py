# -*- coding: utf-8 -*-
"""Bundled scripts."""

# yapf: disable

# Standard library imports
import os.path as osp


SCRIPTS_PATH = osp.dirname(osp.realpath(__file__))
VSCODE_INSTALL_SCRIPT = osp.join(SCRIPTS_PATH, 'vscodeinstall.py')

# yapf: enable
