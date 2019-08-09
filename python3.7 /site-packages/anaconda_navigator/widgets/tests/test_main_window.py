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
from qtpy.QtCore import Qt, QTimer
import pytest

# Local imports
from anaconda_navigator.utils.fixtures import tmpconfig
from anaconda_navigator.widgets.main_window import MainWindow


# yapf: enable

xfail = pytest.mark.xfail
tmpconfig


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def botmain(qtbot, tmpconfig):
    tmpconfig.set('main', 'hide_quit_dialog', True)
    tmpconfig.set('main', 'hide_quit_dialog', True)
    tmpconfig.set('main', 'hide_update_dialog', True)
    widget = MainWindow(config=tmpconfig)
    qtbot.addWidget(widget)
    widget.showMaximized()
    return qtbot, widget


# --- Tests
# -----------------------------------------------------------------------------
def test_all(qtbot, tmpconfig):
    tmpconfig.set('main', 'hide_quit_dialog', True)
    tmpconfig.set('main', 'hide_quit_dialog', True)
    tmpconfig.set('main', 'hide_update_dialog', True)
    widget = MainWindow(config=tmpconfig)
    qtbot.addWidget(widget)
    with qtbot.waitSignal(widget.sig_ready, timeout=60000, raising=True):
        widget.showMaximized()


def test_home_env(qtbot, tmpconfig):
    tmpconfig.set('main', 'hide_quit_dialog', True)
    tmpconfig.set('main', 'hide_quit_dialog', True)
    tmpconfig.set('main', 'hide_update_dialog', True)
    widget = MainWindow(
        tab_home=True,
        tab_environments=True,
        tab_project=False,
        tab_community=False,
        tab_learning=False,
        config=tmpconfig,
    )

    qtbot.addWidget(widget)
    with qtbot.waitSignal(widget.sig_ready, timeout=30000, raising=True):
        widget.showMaximized()


def notest_projects(qtbot, tmpconfig):
    tmpconfig.set('main', 'hide_quit_dialog', True)
    tmpconfig.set('main', 'hide_quit_dialog', True)
    tmpconfig.set('main', 'hide_update_dialog', True)
    widget = MainWindow(
        tab_home=False,
        tab_environments=False,
        tab_project=True,
        tab_community=False,
        tab_learning=False,
        config=tmpconfig,
    )
    qtbot.addWidget(widget)

    def _interact():
        with qtbot.waitSignal(
            widget._dialog_project_action.accepted,
            timeout=10000,
            raising=True
        ):
            widget._dialog_project_action.accept()

    timer = QTimer()
    timer.setInterval(10000)
    timer.timeout.connect(_interact)
    timer.start()

    with qtbot.waitSignal(widget.sig_ready, timeout=30000, raising=True):
        widget.showMaximized()


def test_learning(qtbot, tmpconfig):
    tmpconfig.set('main', 'hide_quit_dialog', True)
    tmpconfig.set('main', 'hide_quit_dialog', True)
    tmpconfig.set('main', 'hide_update_dialog', True)
    widget = MainWindow(
        tab_home=False,
        tab_environments=False,
        tab_project=False,
        tab_community=False,
        tab_learning=True,
        config=tmpconfig,
    )

    qtbot.addWidget(widget)
    with qtbot.waitSignal(widget.sig_ready, timeout=30000, raising=True):
        widget.showMaximized()


def test_community(qtbot, tmpconfig):
    tmpconfig.set('main', 'hide_quit_dialog', True)
    tmpconfig.set('main', 'hide_quit_dialog', True)
    tmpconfig.set('main', 'hide_update_dialog', True)
    widget = MainWindow(
        tab_home=False,
        tab_environments=False,
        tab_project=False,
        tab_community=True,
        tab_learning=False,
        config=tmpconfig,
    )

    qtbot.addWidget(widget)
    with qtbot.waitSignal(widget.sig_ready, timeout=30000, raising=True):
        widget.showMaximized()


# def test_versions(botwin):
#    bot, widget, config = botwin
#
#    packages = {'anaconda-navigator': {'versions': ['1.0.0', '1.1.1']}}
#    widget.check_for_updates(packages, '1.1.1')
#    assert not widget.button_update_available.isVisible()
#    widget.check_for_updates(packages, '1.1.1dev')
#    assert widget.button_update_available.isVisible()
#    widget.check_for_updates(packages, '1.2')
#    assert not widget.button_update_available.isVisible()
#    widget.check_for_updates(packages, '1.1')
#    assert widget.button_update_available.isVisible()


def test_geo_save(qtbot, tmpconfig):
    tmpconfig.set('main', 'hide_quit_dialog', True)
    tmpconfig.set('main', 'hide_quit_dialog', True)
    tmpconfig.set('main', 'hide_update_dialog', True)
    widget = MainWindow(config=tmpconfig)
    qtbot.addWidget(widget)
    with qtbot.waitSignal(widget.sig_ready, timeout=60000, raising=True):
        pass
    widget.close()
    assert tmpconfig.get('main', 'geo')


class TestMainWindowInteractions:
    def test_dialog_about(self, botmain):
        def _interact():
            dlg = widget._dialog_about
            dlg.accept()

        bot, widget = botmain
        with bot.waitSignal(widget.sig_ready, timeout=60000, raising=True):
            pass
        timer = QTimer()
        timer.setInterval(5000)
        timer.timeout.connect(_interact)
        timer.start()
        widget.show_about()

    def test_dialog_channels(self, botmain):
        def _interact():
            dlg = widget._dialog_channels
            dlg.reject()

        bot, widget = botmain
        with bot.waitSignal(widget.sig_ready, timeout=60000, raising=True):
            pass
        timer = QTimer()
        timer.setInterval(5000)
        timer.timeout.connect(_interact)
        timer.start()
        bot.mouseClick(widget.tab_home.button_channels, Qt.LeftButton)

    def test_dialog_licenses(self, botmain):
        def _interact():
            dlg = widget._dialog_licenses
            dlg.accept()

        bot, widget = botmain
        with bot.waitSignal(widget.sig_ready, timeout=60000, raising=True):
            pass
        timer = QTimer()
        timer.setInterval(5000)
        timer.timeout.connect(_interact)
        timer.start()
        widget.show_license_manager()

    def test_dialog_logs(self, botmain):
        def _interact():
            dlg = widget._dialog_logs
            dlg.accept()

        bot, widget = botmain
        with bot.waitSignal(widget.sig_ready, timeout=60000, raising=True):
            pass
        timer = QTimer()
        timer.setInterval(10000)
        timer.timeout.connect(_interact)
        timer.start()
        widget.show_log_viewer()

    def test_dialog_preferences(self, botmain):
        def _interact():
            dlg = widget._dialog_preferences
            dlg.reject()

        bot, widget = botmain
        with bot.waitSignal(widget.sig_ready, timeout=60000, raising=True):
            pass
        timer = QTimer()
        timer.setInterval(5000)
        timer.timeout.connect(_interact)
        timer.start()
        widget.show_preferences()
