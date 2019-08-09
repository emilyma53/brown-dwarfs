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
from qtpy.QtCore import Qt
import pytest

# Local imports
from anaconda_navigator.utils.fixtures import tmpconfig
from anaconda_navigator.widgets.dialogs.quit import (ClosePackageManagerDialog,
                                                     QuitApplicationDialog,
                                                     QuitBusyDialog,
                                                     QuitRunningAppsDialog)


# yapf: enable

tmpconfig
RUNNING_PROCESSES = [
    {
        'pids': [12, 123, 412],
        'package': 'test-app-1',
        'command': 'some command',
        'prefix': '/some/prefix',
    },
    {
        'pids': [345, 6788, 4112],
        'package': 'test-app-2',
        'command': 'some-command-2',
        'prefix': '/some/prefix',
    },
    {
        'pids': [345, 6788, 4112],
        'package': 'test-app-3',
        'command': 'some-command-3',
        'prefix': '/some/prefix',
    },
]
APP_IN_LIST = RUNNING_PROCESSES[0]['package']


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def botquittrue(qtbot, tmpconfig):
    tmpconfig.set('main', 'hide_quit_dialog', True)
    widget = QuitApplicationDialog(config=tmpconfig)
    widget.show()
    qtbot.addWidget(widget)
    qtbot.config = tmpconfig
    return qtbot, widget


@pytest.fixture
def botquitfalse(qtbot, tmpconfig):
    tmpconfig.set('main', 'hide_quit_dialog', False)
    widget = QuitApplicationDialog(config=tmpconfig)
    widget.show()
    qtbot.addWidget(widget)
    qtbot.config = tmpconfig
    return qtbot, widget


@pytest.fixture
def botquitbusy(qtbot):
    widget = QuitBusyDialog()
    widget.show()
    qtbot.addWidget(widget)
    qtbot.config = tmpconfig
    return qtbot, widget


@pytest.fixture
def closecondawidget(qtbot):
    widget = ClosePackageManagerDialog()
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


@pytest.fixture
def botquitrunningappshide(qtbot, tmpconfig):
    tmpconfig.set('main', 'running_apps_to_close', [APP_IN_LIST])
    tmpconfig.set('main', 'hide_running_apps_dialog', True)
    widget = QuitRunningAppsDialog(
        running_processes=RUNNING_PROCESSES, config=tmpconfig
    )
    widget.show()
    qtbot.addWidget(widget)
    qtbot.config = tmpconfig
    return qtbot, widget


@pytest.fixture
def botquitrunningappsshow(qtbot, tmpconfig):
    tmpconfig.set('main', 'running_apps_to_close', [APP_IN_LIST])
    tmpconfig.set('main', 'hide_running_apps_dialog', False)
    widget = QuitRunningAppsDialog(
        running_processes=RUNNING_PROCESSES, config=tmpconfig
    )
    widget.show()
    qtbot.addWidget(widget)
    qtbot.config = tmpconfig
    return qtbot, widget


# --- Tests
# -----------------------------------------------------------------------------
class TestQuitDialog:
    def test_hide(self, botquitfalse):
        qtbot, widget = botquitfalse
        assert widget.checkbox.checkState() == Qt.Unchecked

    def test_show(self, botquittrue):
        qtbot, widget = botquittrue
        assert widget.checkbox.checkState() == Qt.Checked

    def test_accept(self, botquitfalse):
        qtbot, widget = botquitfalse
        qtbot.mouseClick(widget.checkbox, Qt.LeftButton)
        with qtbot.waitSignal(widget.accepted, 1000, True):
            qtbot.mouseClick(widget.button_ok, Qt.LeftButton)
        assert widget.config.get('main', 'hide_quit_dialog')

    def test_reject(self, botquittrue):
        qtbot, widget = botquittrue
        qtbot.mouseClick(widget.checkbox, Qt.LeftButton)
        with qtbot.waitSignal(widget.rejected, 1000, True):
            qtbot.mouseClick(widget.button_cancel, Qt.LeftButton)
        assert widget.config.get('main', 'hide_quit_dialog')


class TestQuitBusyDialog:
    def test_accept(self, botquitbusy):
        qtbot, widget = botquitbusy
        with qtbot.waitSignal(widget.accepted, 1000, True):
            qtbot.mouseClick(widget.button_ok, Qt.LeftButton)

    def test_reject(self, botquitbusy):
        qtbot, widget = botquitbusy
        with qtbot.waitSignal(widget.rejected, 1000, True):
            qtbot.mouseClick(widget.button_cancel, Qt.LeftButton)


class TestCloseCondaDialog:
    def test_ok(self, closecondawidget):
        qtbot, widget = closecondawidget
        with qtbot.waitSignal(widget.accepted, 1000, True):
            qtbot.mouseClick(widget.button_ok, Qt.LeftButton)

    def test_cancel(self, closecondawidget):
        qtbot, widget = closecondawidget
        with qtbot.waitSignal(widget.rejected, 1000, True):
            qtbot.mouseClick(widget.button_cancel, Qt.LeftButton)


class TestQuitRunningAppsDialog:
    def test_hide(self, botquitrunningappshide):
        qtbot, widget = botquitrunningappshide
        assert widget.checkbox.checkState() == Qt.Checked

    def test_show(self, botquitrunningappsshow):
        qtbot, widget = botquitrunningappsshow
        assert widget.checkbox.checkState() == Qt.Unchecked

    def test_accept(self, botquitrunningappsshow):
        qtbot, widget = botquitrunningappsshow
        item = widget.list.item(0)
        item.set_checked(False)
        with qtbot.waitSignal(widget.accepted, 5000, True):
            qtbot.mouseClick(widget.button_close, Qt.LeftButton)
        apps = qtbot.config.get('main', 'running_apps_to_close')
        assert apps == []

    def test_accept_2(self, botquitrunningappsshow):
        qtbot, widget = botquitrunningappsshow
        item = widget.list.item(1)
        item.set_checked(True)
        with qtbot.waitSignal(widget.accepted, 5000, True):
            qtbot.mouseClick(widget.button_close, Qt.LeftButton)
        apps = qtbot.config.get('main', 'running_apps_to_close')
        assert apps == ['test-app-1', 'test-app-2']

    def test_reject(self, botquitrunningappsshow):
        qtbot, widget = botquitrunningappsshow
        item = widget.list.item(2)
        item.set_checked(True)
        with qtbot.waitSignal(widget.rejected, 5000, True):
            qtbot.mouseClick(widget.button_cancel, Qt.LeftButton)
        apps = qtbot.config.get('main', 'running_apps_to_close')
        assert apps == ['test-app-1']
