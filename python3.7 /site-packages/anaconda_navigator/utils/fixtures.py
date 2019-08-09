# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Pytest testing utilities."""

# Standard library imports
import shutil
import tempfile

# Third party imports
import pytest
import requests

# Local imports
from anaconda_navigator.api.anaconda_api import AnacondaAPI
from anaconda_navigator.config.main import CONF_VERSION, DEFAULTS
from anaconda_navigator.config.user import UserConfig


@pytest.fixture(scope='function')
def tmpconfig(request):
    """Return a temporal configuration object and delete after used."""
    SUBFOLDER = tempfile.mkdtemp()
    CONF = UserConfig(
        'anaconda-navigator-test',
        defaults=DEFAULTS,
        version=CONF_VERSION,
        subfolder=SUBFOLDER,
        raw_mode=True,
    )
    CONF.reset_to_defaults()
    AnacondaAPI().client_set_api_url('https://api.anaconda.org')

    def fin():
        shutil.rmtree(SUBFOLDER)

    request.addfinalizer(fin)
    return CONF


@pytest.fixture
def tmpfolder(request):
    """Return a temporal folder path and delete after used."""
    folder = tempfile.mkdtemp()

    def fin():
        shutil.rmtree(folder)

    request.addfinalizer(fin)
    return folder


@pytest.fixture
def tmpfile(request):
    """Return a temporal file path and delete after used."""
    _, path = tempfile.mkstemp()

    def fin():
        print('tmpfile finalizer')

    request.addfinalizer(fin)
    return path


@pytest.fixture(params=["events", "videos", "webinars"])
def tmpjsonfile_production(request):
    """Return a temporal file path with downloaded content."""
    content_base_uri = 'http://anaconda.com/api/{0}?items_per_page=all'
    url = content_base_uri.format(request.param)
    _, path = tempfile.mkstemp(suffix='json', text=True)
    api = AnacondaAPI()
    r = requests.get(url, proxies=api.conda_load_proxy_config())
    with open(path, 'w') as f:
        f.write(r.text)

    def fin():
        print("Finalizing production {0} check".format(request.param))

#        shutil.rmtree(path)

    request.addfinalizer(fin)
    return path
