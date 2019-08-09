# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Styles for the application."""

# yapf: disable

# Standard library imports
import ast
import os
import re
import string

# Local imports
from navigator_updater.config import DEV
from navigator_updater.static.css import (GLOBAL_SASS_STYLES_PATH,
                                          GLOBAL_STYLES_PATH)
from navigator_updater.static.images import IMAGE_PATH

# This is a development dependency to parse the sass style sheet
try:
    import sass
    sass_module_installed = True
except Exception:
    sass_module_installed = False

# yapf: enable

BLUR_SIZE = 10


class SassVariables(object):
    """Enum to hold SASS defined variables."""

    def __init__(self):
        """Enum to hold SASS defined variables."""
        self.SHADOW_BLUR_RADIUS = 7  # Used for dialogs
        self.WIDGET_APPLICATION_TOTAL_HEIGHT = 200
        self.WIDGET_APPLICATION_TOTAL_WIDTH = 200
        self.WIDGET_CONTENT_PADDING = 5
        self.WIDGET_CONTENT_TOTAL_HEIGHT = 200
        self.WIDGET_CONTENT_TOTAL_WIDTH = 200
        self.WIDGET_CONTENT_PADDING = 5
        self.WIDGET_CONTENT_MARGIN = 5
        self.WIDGET_ENVIRONMENT_TOTAL_HEIGHT = 50
        self.WIDGET_ENVIRONMENT_TOTAL_WIDTH = 25
        self.WIDGET_APPLICATION_TOTAL_WIDTH = 260
        self.WIDGET_APPLICATION_TOTAL_HEIGHT = 295
        self.WIDGET_CHANNEL_DIALOG_WIDTH = 400
        self.WIDGET_CHANNEL_TOTAL_WIDTH = 300
        self.WIDGET_CHANNEL_TOTAL_HEIGHT = 40
        self.WIDGET_CHANNEL_PADDING = 5
        self.WIDGET_RUNNING_APPS_WIDTH = 450
        self.WIDGET_RUNNING_APPS_TOTAL_WIDTH = 350
        self.WIDGET_RUNNING_APPS_TOTAL_HEIGHT = 55
        self.WIDGET_RUNNING_APPS_PADDING = 10

    def __repr__(self):
        """Return a pretty formtated representation of the enum."""
        keys = []
        representation = 'SASS variables enum: \n'
        for key in self.__dict__:
            if key[0] in string.ascii_uppercase:
                keys.append(key)

        for key in sorted(keys):
            representation += '    {0} = {1}\n'.format(key, self.__dict__[key])
        return representation


SASS_VARIABLES = SassVariables()


def load_sass_variables(data):
    """Parse Sass file styles and get custom values for used in code."""
    global SASS_VARIABLES
    pattern = re.compile(r'[$]\S*:.*?;')
    variables = re.findall(pattern, data)
    for var in variables:
        name, value = var[1:-1].split(':')
        if name[0] in string.ascii_uppercase:
            value = value.strip()
            try:
                value = ast.literal_eval(value)
            except Exception:
                pass
            setattr(SASS_VARIABLES, name, value)
    return SASS_VARIABLES


def load_style_sheet():
    """Load css styles file and parse to include custom variables."""
    with open(GLOBAL_SASS_STYLES_PATH, 'r') as f:
        sass_data = f.read()

    load_sass_variables(sass_data)

    if sass_module_installed and DEV:
        # Needed on OSX
        try:
            sass_data = sass_data.encode()
        except Exception:
            pass

        try:
            # Using https://github.com/dahlia/libsass-python
            data = sass.compile(string=sass_data)
        except Exception:
            pass

        try:
            # Using https://github.com/pistolero/python-scss
            data = sass.compile_string(sass_data)
        except Exception:
            pass

        # Needed on OSX
        try:
            data = data.decode()
        except Exception:
            pass

        with open(GLOBAL_STYLES_PATH, 'w') as f:
            f.write(data)

    with open(GLOBAL_STYLES_PATH, 'r') as f:
        data = f.read()

    if os.name == 'nt':
        data = data.replace('$IMAGE_PATH', IMAGE_PATH.replace('\\', '/'))
    else:
        data = data.replace('$IMAGE_PATH', IMAGE_PATH)

    return data
