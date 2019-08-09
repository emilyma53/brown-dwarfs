# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""
Tests the about dialog.
"""

# yapf: disable

# Third party imports
from qtpy.QtCore import Qt
import pytest

# Local imports
from anaconda_navigator.utils.fixtures import tmpconfig
from anaconda_navigator.widgets.dialogs.about import AboutDialog


# yapf: enable

tmpconfig


@pytest.fixture()
def aboutdialog(qtbot):
    widget = AboutDialog()
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


def test_ok(aboutdialog):
    qtbot, widget = aboutdialog
    with qtbot.waitSignal(widget.accepted, 1000, True):
        qtbot.mouseClick(widget.button_ok, Qt.LeftButton)


def test_cancel(aboutdialog):
    qtbot, widget = aboutdialog
    with qtbot.waitSignal(widget.rejected, 1000, True):
        qtbot.keyPress(widget, Qt.Key_Escape)


def test_link(aboutdialog):
    qtbot, widget = aboutdialog
    with qtbot.waitSignal(widget.sig_url_clicked, 1000, True):
        qtbot.mouseClick(widget.button_link, Qt.LeftButton)
