# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Tests for preferences dialog."""

# yapf: disable

# Third party imports
from flaky import flaky
from qtpy.QtCore import Qt
import pytest

# Local imports
from anaconda_navigator.config.main import DEFAULTS
from anaconda_navigator.utils.fixtures import tmpconfig, tmpfile
from anaconda_navigator.widgets.dialogs.preferences import PreferencesDialog


# yapf: enable

tmpconfig
tmpfile
xfail = pytest.mark.xfail
MAIN_SECTION = DEFAULTS[0][-1]
CHECK_OPTIONS = [
    'provide_analytics',
    'hide_quit_dialog',
    'hide_update_dialog',
    'hide_running_apps_dialog',
    'enable_high_dpi_scaling',
]
ALL_OPTIONS = CHECK_OPTIONS[:]
ALL_OPTIONS.append('anaconda_api_url')


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def botpreferences(qtbot, tmpconfig):
    widget = PreferencesDialog(config=tmpconfig)
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


# --- Tests
# -----------------------------------------------------------------------------
def test_simple(botpreferences):
    qtbot, dialog = botpreferences
    assert dialog.widgets
    assert not dialog.button_ok.isEnabled()  # no change yet
    assert dialog.button_reset.isEnabled()
    assert dialog.button_cancel.isEnabled()

    for option, default_value in MAIN_SECTION.items():
        if option in CHECK_OPTIONS:
            widget = dialog.widget_for_option(option)
            assert widget.get_value() == default_value


def test_options_accept(botpreferences):
    qtbot, dialog = botpreferences
    for option, default_value in MAIN_SECTION.items():
        if option in CHECK_OPTIONS:
            widget = dialog.widget_for_option(option)
            widget.set_value(not default_value)

    with qtbot.waitSignal(dialog.accepted, timeout=5000, raising=True):
        qtbot.mouseClick(dialog.button_ok, Qt.LeftButton)

    for option, default_value in MAIN_SECTION.items():
        if option in CHECK_OPTIONS:
            widget = dialog.widget_for_option(option)
            assert widget.get_value() is not default_value
            assert dialog.get_option(option) is not default_value
    assert not dialog.isVisible()


def test_options_cancel(botpreferences):
    qtbot, dialog = botpreferences
    for option, default_value in MAIN_SECTION.items():
        if option in CHECK_OPTIONS:
            widget = dialog.widget_for_option(option)
            widget.set_value(not default_value)
            print(widget.option, not default_value)

    with qtbot.waitSignal(dialog.rejected, timeout=5000, raising=True):
        qtbot.mouseClick(dialog.button_cancel, Qt.LeftButton)

    print('\n')
    for option, default_value in MAIN_SECTION.items():
        if option in CHECK_OPTIONS:
            widget = dialog.widget_for_option(option)
            print(widget.option, dialog.get_option(option))
            assert dialog.get_option(option) == default_value
    assert not dialog.isVisible()


def test_get_defaults(botpreferences):
    qtbot, dialog = botpreferences
    for option, default_value in MAIN_SECTION.items():
        if option in CHECK_OPTIONS:
            assert default_value == dialog.get_option_default(option)


def test_set_defaults(botpreferences):
    qtbot, dialog = botpreferences
    for option, default_value in MAIN_SECTION.items():
        if option in CHECK_OPTIONS:
            widget = dialog.widget_for_option(option)
            widget.set_value(not default_value)
            dialog.set_option_default(option)
            assert dialog.get_option(option) == default_value


def test_options_changed_back(botpreferences):
    qtbot, dialog = botpreferences
    for option, default_value in MAIN_SECTION.items():
        if option in CHECK_OPTIONS:
            widget = dialog.widget_for_option(option)
            dialog.widgets_changed.add(widget)
            dialog.options_changed(value=default_value, widget=widget)


@xfail
def test_api_valid(botpreferences):
    qtbot, dialog = botpreferences
    qtbot.keyClicks(dialog.widgets[0], 'https://api.beta.anaconda.org')
    with qtbot.waitSignal(dialog.accepted, timeout=5000, raising=True):
        qtbot.mouseClick(dialog.button_ok, Qt.LeftButton)
    assert not dialog.isVisible()


def test_api_invalid(botpreferences):
    qtbot, dialog = botpreferences
    qtbot.keyClicks(dialog.widgets[0], '*&**&')
    with qtbot.waitSignal(dialog.sig_check_ready, timeout=5000, raising=True):
        qtbot.mouseClick(dialog.button_ok, Qt.LeftButton)
    assert dialog.widgets[0].label_information.toolTip()
    assert dialog.button_ok.isEnabled() is False
    assert dialog.isVisible()


@xfail
def test_api_ssl(botpreferences):
    qtbot, dialog = botpreferences
    qtbot.keyClicks(dialog.widgets[0], 'https://api.beta.anaconda.org')
    widget = dialog.widget_for_option('ssl_verification')
    widget.set_value(False)
    widget.check_value(False)
    dialog.widgets_changed.add(widget)
    with qtbot.waitSignal(dialog.accepted, timeout=5000, raising=True):
        qtbot.mouseClick(dialog.button_ok, Qt.LeftButton)
    assert not dialog.isVisible()


def test_api_close(botpreferences):
    qtbot, dialog = botpreferences
    qtbot.keyClicks(dialog.widgets[0], 'https://beta.anaconda.org')  # no .api
    with qtbot.waitSignal(dialog.sig_check_ready, timeout=10000, raising=True):
        qtbot.mouseClick(dialog.button_ok, Qt.LeftButton)
    assert dialog.widgets[0].label_information.toolTip()
    assert dialog.button_ok.isEnabled() is False
    assert dialog.isVisible()


def test_api_close_2(botpreferences):
    qtbot, dialog = botpreferences
    qtbot.keyClicks(dialog.widgets[0], 'https://beta.anaconda.org/')  # no .api
    with qtbot.waitSignal(dialog.sig_check_ready, timeout=10000, raising=True):
        qtbot.mouseClick(dialog.button_ok, Qt.LeftButton)
    assert dialog.button_ok.isEnabled() is False
    assert dialog.isVisible()


def test_options_reset_cancel(botpreferences):
    qtbot, dialog = botpreferences
    for option, default_value in MAIN_SECTION.items():
        if option in CHECK_OPTIONS:
            widget = dialog.widget_for_option(option)
            widget.set_value(not default_value)

    with qtbot.waitSignal(dialog.sig_check_ready, timeout=5000, raising=True):
        qtbot.mouseClick(dialog.button_ok, Qt.LeftButton)

    with qtbot.waitSignal(dialog.sig_reset_ready, timeout=5000, raising=True):
        qtbot.mouseClick(dialog.button_reset, Qt.LeftButton)

    with qtbot.waitSignal(dialog.rejected, timeout=5000, raising=True):
        qtbot.mouseClick(dialog.button_cancel, Qt.LeftButton)

    for option, default_value in MAIN_SECTION.items():
        if option in CHECK_OPTIONS:
            assert dialog.get_option(option) != default_value

    assert not dialog.isVisible()


@flaky(max_runs=2, min_passes=1)
def test_options_reset_accept(botpreferences):
    qtbot, dialog = botpreferences
    for option, default_value in MAIN_SECTION.items():
        if option in CHECK_OPTIONS:
            widget = dialog.widget_for_option(option)
            widget.set_value(not default_value)

    with qtbot.waitSignal(dialog.sig_check_ready, timeout=10000, raising=True):
        qtbot.mouseClick(dialog.button_ok, Qt.LeftButton)

    with qtbot.waitSignal(dialog.sig_reset_ready, timeout=10000, raising=True):
        qtbot.mouseClick(dialog.button_reset, Qt.LeftButton)

    with qtbot.waitSignal(dialog.accepted, timeout=10000, raising=True):
        qtbot.mouseClick(dialog.button_ok, Qt.LeftButton)

    for option, default_value in MAIN_SECTION.items():
        if option in CHECK_OPTIONS:
            assert dialog.get_option(option) == default_value

    assert not dialog.isVisible()


def test_ssl_options_true(botpreferences):
    qtbot, dialog = botpreferences
    assert dialog.widget_for_option('ssl_verification').isChecked()
    assert dialog.widget_for_option('ssl_certificate').isEnabled()


def test_ssl_options_false(botpreferences):
    qtbot, dialog = botpreferences
    ssl_verify = dialog.widget_for_option('ssl_verification')
    ssl_verify.set_value(False)
    assert not dialog.widget_for_option('ssl_verification').isChecked()
    assert not dialog.widget_for_option('ssl_certificate').isEnabled()


def test_ssl_options_path_invalid(botpreferences):
    qtbot, dialog = botpreferences
    ssl_cert = dialog.widget_for_option('ssl_certificate')
    ssl_cert.set_value('rubishpath/')

    with qtbot.waitSignal(dialog.sig_check_ready, timeout=10000, raising=True):
        qtbot.mouseClick(dialog.button_ok, Qt.LeftButton)
    assert not dialog.button_ok.isEnabled()


def test_ssl_options_path_valid(botpreferences, tmpfile):
    qtbot, dialog = botpreferences
    ssl_cert = dialog.widget_for_option('ssl_certificate')
    ssl_cert.set_value(tmpfile)

    with qtbot.waitSignal(dialog.accepted, timeout=10000, raising=True):
        qtbot.mouseClick(dialog.button_ok, Qt.LeftButton)
    assert dialog.button_ok.isEnabled()
