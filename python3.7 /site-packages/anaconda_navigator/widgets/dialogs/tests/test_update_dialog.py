# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Tests for update dialog."""

# yapf: disable

# Third party imports
from qtpy.QtCore import Qt
import pytest

# Local imports
from anaconda_navigator.utils.fixtures import tmpconfig
from anaconda_navigator.widgets.dialogs.update import DialogUpdateApplication


# yapf: enable

tmpconfig


@pytest.fixture(params=[False, True])
def updatedialog(qtbot, tmpconfig, request):
    widget = DialogUpdateApplication(
        "1.0", config=tmpconfig, startup=request.param
    )
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


def test_yes(updatedialog):
    qtbot, widget = updatedialog
    with qtbot.waitSignal(widget.accepted, 1000, True):
        qtbot.mouseClick(widget.button_yes, Qt.LeftButton)
    assert not widget.config.get('main', 'hide_update_dialog')


def test_no(updatedialog):
    qtbot, widget = updatedialog
    with qtbot.waitSignal(widget.rejected, 1000, True):
        qtbot.mouseClick(widget.button_no, Qt.LeftButton)
    assert not widget.config.get('main', 'hide_update_dialog')


def test_no_show(updatedialog):
    qtbot, widget = updatedialog
    with qtbot.waitSignal(widget.rejected, 1000, True):
        qtbot.mouseClick(widget.button_no_show, Qt.LeftButton)
    assert widget.config.get('main', 'hide_update_dialog')
