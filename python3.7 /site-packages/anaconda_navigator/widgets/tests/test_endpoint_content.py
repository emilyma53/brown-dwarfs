# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Tests for quit-like dialogs."""

# yapf: disable

# Third party imports
import requests

# Local imports
from anaconda_navigator.widgets.main_window import MainWindow


# yapf: enable


# --- Tests
# -----------------------------------------------------------------------------
def test_video_endpoint():
    videos_url = MainWindow.VIDEOS_URL
    r = requests.get(videos_url)
    data = r.json()
    errors = []
    if data:
        for item in data:
            url = item.get('video')
            url = url.replace('<p>', '').replace('</p>', '')

            invalid = True
            try:
                r = requests.head(url)
                invalid = False
            except Exception:
                pass

            if invalid or r.status_code == 404:
                errors.append(item)

    if errors:
        print('The following {} urls are not working!'.format(len(errors)))
        for i, error in enumerate(errors):
            print(i + 1)
            print(error.get('title'))
            print(error.get('video'))
            print('\n')

    assert len(errors) == 0
