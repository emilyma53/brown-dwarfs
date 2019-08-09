# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Tests for environment-related dialogs."""

# yapf: disable

# Third party imports
from qtpy.QtCore import Qt
import pytest

# Local imports
from anaconda_navigator.widgets.dialogs import packages


# yapf: enable


class WorkerMock():
    prefix = 'some/prefix'


PACKAGES = ['boom']
OUTPUT_INSTALL_SUCCESS = {
    'success':
    True,
    'error':
    '',
    'exception_name':
    '',
    'actions': [
        {
            'LINK': [
                {
                    'name': 'boom',
                    'version': '1.5',
                    'channel': 'goanpeca',
                    'dist_name': 'boom-1.5-build0',
                },
                {
                    'name': 'dep-1',
                    'version': '1.6',
                    'channel': 'goanpeca',
                    'dist_name': 'dep-1-1.6-build0',
                },
            ],
            'UNLINK': [
                {
                    'name': 'boom',
                    'version': '1.4',
                    'channel': 'goanpeca',
                    'dist_name': 'boom-1.4-build0',
                },
                {
                    'name': 'dep-1',
                    'version': '1.7',
                    'channel': 'goanpeca',
                    'dist_name': 'dep-1-1.7-build0'
                },
            ],
        },
    ],
}

OUTPUT_REMOVE_SUCCESS = {
    'success':
    True,
    'error':
    '',
    'exception_name':
    '',
    'actions': [
        {
            'LINK': [],
            'UNLINK': [
                {
                    'name': 'boom',
                    'version': '1.4',
                    'channel': 'goanpeca',
                    'dist_name': 'boom-1.4-build1',
                },
            ],
        },
    ],
}

OUTPUT_INSTALL_FAIL = {
    'success': False,
    'error': 'Something happened!',
    'exception_name': 'WeirdException',
    'actions': [],
}

OUTPUT_EMPTY = {}


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def botpackages(qtbot):
    """Return bot and widget."""
    widget = packages.PackagesDialog(packages=PACKAGES, remove_only=False)
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


@pytest.fixture
def botpackagesremove(qtbot):
    """Return bot and widget."""
    widget = packages.PackagesDialog(packages=PACKAGES, remove_only=True)
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


# --- Fixtures
# -----------------------------------------------------------------------------
def test_install_success(botpackages):
    bot, dialog = botpackages
    dialog.setup(WorkerMock(), OUTPUT_INSTALL_SUCCESS, None)
    assert dialog.button_ok.isEnabled()
    assert dialog.button_cancel.isEnabled()
    with bot.waitSignal(dialog.accepted, timeout=5000, raising=True):
        bot.keyPress(dialog.button_ok, Qt.Key_Enter)


def test_remove_success(botpackagesremove):
    bot, dialog = botpackagesremove
    dialog.setup(WorkerMock(), OUTPUT_REMOVE_SUCCESS, None)
    with bot.waitSignal(dialog.accepted, timeout=10000, raising=False):
        pass
    assert dialog.button_ok.isEnabled()
    assert dialog.button_cancel.isEnabled()
    with bot.waitSignal(dialog.accepted, timeout=5000, raising=True):
        bot.keyPress(dialog.button_ok, Qt.Key_Enter)


def test_fail(botpackages):
    bot, dialog = botpackages
    dialog.setup(WorkerMock(), OUTPUT_INSTALL_FAIL, None)
    assert not dialog.button_ok.isEnabled()
    assert dialog.button_cancel.isEnabled()
    with bot.waitSignal(dialog.rejected, timeout=5000, raising=True):
        dialog.reject()


def test_output_empty(botpackages):
    bot, dialog = botpackages
    dialog.setup(WorkerMock(), OUTPUT_EMPTY, None)
    assert not dialog.button_ok.isEnabled()
    assert dialog.button_cancel.isEnabled()
    with bot.waitSignal(dialog.rejected, timeout=5000, raising=True):
        dialog.reject()


def test_output_wrong(botpackages):
    bot, dialog = botpackages
    dialog.setup(WorkerMock(), [], None)
    assert not dialog.button_ok.isEnabled()
    assert dialog.button_cancel.isEnabled()
    with bot.waitSignal(dialog.rejected, timeout=5000, raising=True):
        dialog.reject()
