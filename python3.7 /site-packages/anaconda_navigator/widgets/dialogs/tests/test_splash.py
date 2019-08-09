# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""
Tests for splash screens.
"""

# Third party imports
from qtpy.QtCore import Qt  # analysis:ignore
import pytest
import pytestqt.qtbot as qtbot  # analysis:ignore

# Local imports
from anaconda_navigator.utils.fixtures import tmpconfig
from anaconda_navigator.widgets.dialogs.splash import FirstSplash, SplashScreen


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def botfirstsplash(qtbot, tmpconfig):
    widget = FirstSplash()
    widget.config = tmpconfig  # Patch with a temporal config file
    widget.setup()
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


# --- Tests
# -----------------------------------------------------------------------------
def test_first_splash_ok(botfirstsplash):
    qtbot, widget = botfirstsplash
    qtbot.mouseClick(widget.button_ok, Qt.LeftButton)
    show_startup = widget.config.get('main', 'show_startup')
    assert show_startup


def test_first_splash_ok_dont_show(botfirstsplash):
    qtbot, widget = botfirstsplash
    qtbot.mouseClick(widget.button_ok_dont_show, Qt.LeftButton)
    show_startup = widget.config.get('main', 'show_startup')
    assert not show_startup


def test_first_splash_enable_analytics(botfirstsplash):
    qtbot, widget = botfirstsplash
    qtbot.mouseClick(widget.checkbox_track, Qt.LeftButton)
    qtbot.mouseClick(widget.checkbox_track, Qt.LeftButton)
    qtbot.mouseClick(widget.button_ok, Qt.LeftButton)
    provide_analytics = widget.config.get('main', 'provide_analytics')
    assert provide_analytics


def test_first_splash_disable_analytics(botfirstsplash):
    qtbot, widget = botfirstsplash
    qtbot.mouseClick(widget.checkbox_track, Qt.LeftButton)
    qtbot.mouseClick(widget.button_ok, Qt.LeftButton)
    provide_analytics = widget.config.get('main', 'provide_analytics')
    assert not provide_analytics


def test_first_splash_reject(botfirstsplash):
    qtbot, widget = botfirstsplash
    widget.reject()
    assert widget.isVisible()


def test_splash_screen(qtbot):  # analysis:ignore
    widget = SplashScreen()
    qtbot.addWidget(widget)
    test_message = 'Test message'
    widget.show_message(test_message)
    assert widget.get_message() == test_message
