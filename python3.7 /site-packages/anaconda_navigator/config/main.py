# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Default configuration options."""

# yapf: disable

# Local imports
from anaconda_navigator.config.base import SUBFOLDER
from anaconda_navigator.config.user import UserConfig


# yapf: enable

# -----------------------------------------------------------------------------
# --- Defaults
# -----------------------------------------------------------------------------
DEFAULTS = [
    (
        'main',  # General
        {
            'name': 'Anaconda Navigator',
            'first_run': True,
            'hide_quit_dialog': False,
            'hide_running_apps_dialog': False,
            'hide_update_dialog': False,
            'hide_offline_dialog': True,
            'first_time_offline': True,
            'last_status_is_offline': False,
            'running_apps_to_close': ['anaconda-fusion'],  # Hidden opt
            'show_startup': True,
            'add_default_channels': True,
            'offline_mode': False,

            # --- Package Manager
            'conda_active_channels': None,

            # --- Anaconda Client Configuration, these values are not needed
            'anaconda_api_url': 'https://api.anaconda.org',
            'ssl_verification': True,
            'ssl_certificate': None,
            # Used by batch initial config
            'default_anaconda_api_url': None,
            'default_ssl_certificate': None,

            # --- Anaconda Project Configuration
            'projects_path': None,
            'active_project_path': None,

            # --- Preferences
            'enable_high_dpi_scaling': True,
            'provide_analytics': True,
            'show_application_environments': True,
            'show_application_launch_errors': True,

            # --- Custom links
            'twitter_url': 'https://twitter.com/AnacondaInc',
            'youtube_url': 'https://www.youtube.com/c/continuumio',
            'github_url': 'https://github.com/ContinuumIO',
        },
    ),
    ('home', {
        'vscode_enable': True,
    }),
]

# -----------------------------------------------------------------------------
# --- Config instance
# -----------------------------------------------------------------------------
# IMPORTANT NOTES:
# 1. If you want to *change* the default value of a current option, you need to
#    do a MINOR update in config version, e.g. from 1.0.0 to 1.1.0
# 2. If you want to *remove* options that are no longer needed in our codebase,
#    or if you want to *rename* options, then you need to do a MAJOR update in
#    version, e.g. from 1.0.0 to 2.0.0
# 3. You don't need to touch this value if you're just adding a new option
CONF_VERSION = '2.0.0'
CONF = UserConfig(
    'anaconda-navigator',
    defaults=DEFAULTS,
    version=CONF_VERSION,
    subfolder=SUBFOLDER,
    raw_mode=True,
)
