# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Tests for quit-like dialogs."""

# Third party imports
from qtpy.QtCore import Qt  # analysis:ignore
import pytestqt.qtbot as qtbot  # analysis:ignore

# Local imports
from navigator_updater.widgets.dialogs.main_dialog import MainDialog


def test_main(qtbot):
    widget = MainDialog()
    widget.show()
    with qtbot.waitSignal(widget.sig_ready, timeout=10000):
        pass

    with qtbot.waitSignal(widget.sig_application_updated, timeout=60000):
        qtbot.mouseClick(widget.button_update, Qt.LeftButton)
