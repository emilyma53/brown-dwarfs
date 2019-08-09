# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Tests for Anaconda API functions."""

# yapf: disable

# Standard library imports
import datetime

# Third party imports
import pytest

# Local imports
from anaconda_navigator.api.anaconda_api import _AnacondaAPI
from anaconda_navigator.utils.fixtures import tmpfolder


# yapf: enable

DEFAULT_TIMEOUT = 120000
tmpfolder


def create_date_string(days_delta=30):
    now = datetime.datetime.now()
    year = now.year
    month = now.month
    day = now.day
    new_date = datetime.date(year, month, day)
    new_date += datetime.timedelta(days=days_delta)
    return new_date.strftime('%Y-%m-%d')


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def api(tmpfolder):
    api = _AnacondaAPI()
    return api


# --- Tests
# -----------------------------------------------------------------------------
# def test_license_days_left(api):
#     days_left = api.get_days_left({})
#     assert days_left == 0
#
#     days_left = api.get_days_left({'dummy_key': 'test'})
#     assert days_left == float('inf')

# def test_license_days_left_remaining(api):
#     for day in range(-30, 0):
#         days_left = api.get_days_left({'end_date': create_date_string(day)})
#         assert days_left == 0
#
#     for day in range(30):
#         days_left = api.get_days_left({'end_date': create_date_string(day)})
#         assert days_left == day


def test_conda_data(qtbot, api):
    """"""

    def output_ready(worker, output, error):
        assert error is None
        assert len(output)
        assert 'info' in output
        assert 'processed_info' in output
        assert 'packages' in output
        assert 'applications' in output

    worker = api.conda_data(prefix=api.ROOT_PREFIX)
    with qtbot.waitSignal(
        worker.sig_chain_finished, timeout=DEFAULT_TIMEOUT, raising=True
    ):
        worker.sig_chain_finished.connect(output_ready)


def test_process_packages(api, qtbot):
    BLACKLIST = ['python', 'anaconda-navigator']

    def conda_data_ready(worker, output, error):
        packages = output['packages']
        worker_2 = api.process_packages(
            packages,
            prefix=api.ROOT_PREFIX,
            blacklist=BLACKLIST,
        )
        worker_2.check_packages = packages

        with qtbot.waitSignal(
            worker_2.sig_chain_finished, timeout=DEFAULT_TIMEOUT, raising=True
        ):
            worker_2.sig_chain_finished.connect(process_packages_ready)

    def process_packages_ready(worker, output, error):
        assert error is None
        assert len(output)
        # See: https://github.com/ContinuumIO/navigator/issues/1244
        for package_name in BLACKLIST:
            assert package_name in worker.check_packages

    worker = api.conda_data(prefix=api.ROOT_PREFIX)
    with qtbot.waitSignal(
        worker.sig_chain_finished, timeout=DEFAULT_TIMEOUT, raising=True
    ):
        worker.sig_chain_finished.connect(conda_data_ready)
