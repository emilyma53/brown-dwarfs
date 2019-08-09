# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Tests for login dialog."""

# yapf: disable

# Standard library imports
import os

# Third party imports
from flaky import flaky
from qtpy.QtCore import Qt  # analysis:ignore
import pytest
import pytestqt.qtbot as qtbot  # analysis:ignore

# Local imports
from anaconda_navigator.api.anaconda_api import AnacondaAPI
from anaconda_navigator.utils.fixtures import tmpconfig
from anaconda_navigator.widgets.dialogs.login import AuthenticationDialog


# yapf: enable

NAVIGATOR_TEST_EMAIL = os.environ.get('NAVIGATOR_TEST_EMAIL')
NAVIGATOR_TEST_USERNAME = os.environ.get('NAVIGATOR_TEST_USERNAME')
NAVIGATOR_TEST_PASSWORD = os.environ.get('NAVIGATOR_TEST_PASSWORD')
TEST_CI = os.environ.get('TEST_CI')

xfail = pytest.mark.xfail
skipif = pytest.mark.skipif


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def botlogin(qtbot, tmpconfig):
    tmpconfig.set('main', 'anaconda_api_url', 'https://api.anaconda.org/')
    widget = AuthenticationDialog(api=AnacondaAPI())
    widget.config = tmpconfig  # Patch with a temporal config file
    widget.setup()
    qtbot.addWidget(widget)
    widget.show()
    return qtbot, widget


@pytest.fixture
def botlogin_dev(qtbot, tmpconfig):
    tmpconfig.set(
        'main', 'anaconda_api_url', 'http://develop.anaconda.org/api'
    )
    widget = AuthenticationDialog(api=AnacondaAPI())
    widget.config = tmpconfig  # Patch with a temporal config file
    widget.setup()
    qtbot.addWidget(widget)
    widget.show()
    return qtbot, widget


# --- Tests
# -----------------------------------------------------------------------------
def test_login_button_username_filled(botlogin):
    qtbot, widget = botlogin
    qtbot.keyClicks(widget.text_username, NAVIGATOR_TEST_USERNAME)
    widget.text_password.setText('')
    assert not widget.button_login.isEnabled()


def test_login_button_password_filled(botlogin):
    qtbot, widget = botlogin
    qtbot.keyClicks(widget.text_password, NAVIGATOR_TEST_PASSWORD)
    widget.text_username.setText('')
    assert not widget.button_login.isEnabled()


def test_login_button_filled(botlogin):
    qtbot, widget = botlogin
    qtbot.keyClicks(widget.text_username, 'randomuserstring')
    qtbot.keyClicks(widget.text_password, 'randomuserstringpassword')
    assert widget.button_login.isEnabled()


def test_username_text_valid(botlogin):
    qtbot, widget = botlogin
    qtbot.keyClicks(widget.text_username, '123456test@#$123')
    assert widget.username == '123456test123'

    widget.text_username.setText('')
    qtbot.keyClicks(widget.text_username, 'alpha-alpha_123456789')
    assert widget.username == 'alpha-alpha_123456789'


#@skipif(TEST_CI is None, reason='Test on CI only')
#@flaky(max_runs=4, min_passes=1)
@xfail
def test_username_invalid(botlogin):
    qtbot, widget = botlogin
    qtbot.keyClicks(widget.text_username, 'hopefully-not-an-existing-user')
    qtbot.keyClicks(widget.text_password, NAVIGATOR_TEST_PASSWORD)
    with qtbot.waitSignal(
        signal=widget.sig_authentication_failed, timeout=5000, raising=True
    ):
        qtbot.mouseClick(widget.button_login, Qt.LeftButton)
    assert widget.isVisible()


#@skipif(TEST_CI is None, reason='Test on CI only')
#@flaky(max_runs=4, min_passes=1)
@xfail
def test_username_valid_password_valid(botlogin):
    qtbot, widget = botlogin
    qtbot.keyClicks(widget.text_username, NAVIGATOR_TEST_USERNAME)
    qtbot.keyClicks(widget.text_password, NAVIGATOR_TEST_PASSWORD)
    with qtbot.waitSignal(
        signal=widget.sig_authentication_succeeded, timeout=5000, raising=True
    ):
        qtbot.mouseClick(widget.button_login, Qt.LeftButton)
    assert not widget.isVisible()


#@flaky(max_runs=4, min_passes=1)
@xfail
def test_username_valid_password_invalid(botlogin):
    qtbot, widget = botlogin
    qtbot.keyClicks(widget.text_username, 'goanpeca')
    qtbot.keyClicks(widget.text_password, 'wrongpassword')
    with qtbot.waitSignal(
        signal=widget.sig_authentication_failed, timeout=5000, raising=True
    ):
        qtbot.mouseClick(widget.button_login, Qt.LeftButton)
    assert widget.isVisible()


def test_forgot_username_link(botlogin):
    qtbot, widget = botlogin
    with qtbot.waitSignal(
        signal=widget.sig_url_clicked, timeout=5000, raising=True
    ):
        qtbot.mouseClick(widget.button_forgot_username, Qt.LeftButton)
    assert widget.isVisible()


def test_forgot_password_link(botlogin):
    qtbot, widget = botlogin
    with qtbot.waitSignal(
        signal=widget.sig_url_clicked, timeout=5000, raising=True
    ):
        qtbot.mouseClick(widget.button_forgot_password, Qt.LeftButton)
    assert widget.isVisible()


def test_register_link(botlogin):
    qtbot, widget = botlogin
    with qtbot.waitSignal(
        signal=widget.sig_url_clicked, timeout=5000, raising=True
    ):
        qtbot.mouseClick(widget.button_register, Qt.LeftButton)
    assert widget.isVisible()


def test_update_links(botlogin_dev):
    qtbot, widget = botlogin_dev
    forgot_url = 'http://develop.anaconda.org/account/forgot_username'
    password_url = 'http://develop.anaconda.org/account/forgot_password'
    assert widget.forgot_username_url == forgot_url
    assert widget, forgot_password_url == password_url
