# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Tests for logger window."""

# yapf: disable

# Standard library imports
import logging
import os

# Third party imports
from qtpy.QtCore import Qt
import pytest

# Local imports
from anaconda_navigator.utils.fixtures import tmpfile
from anaconda_navigator.utils.logs import logger, setup_logger
from anaconda_navigator.widgets.dialogs.logger import LogViewerDialog


# yapf: enable

# Constants
TEST_TEXT = 'WARNING TEST MESSAGE'
TEST_TEXT_EXTRA = 'SOMETHING ELSE'
tmpfile


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture()
def loggerbot(qtbot, tmpfile):
    temp_log_folder = os.path.dirname(tmpfile)
    temp_log_filename = os.path.basename(tmpfile + '.log')

    setup_logger(
        log_level=logging.WARNING,
        log_folder=temp_log_folder,
        log_filename=temp_log_filename
    )
    logger.warning(TEST_TEXT)
    logger.warning(TEST_TEXT_EXTRA)
    widget = LogViewerDialog(
        log_folder=temp_log_folder, log_filename=temp_log_filename
    )
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


# --- Tests
# -----------------------------------------------------------------------------
def test_simple(loggerbot):
    qtbot, widget = loggerbot
    data = widget.row_data(0)
    message = data.get('message')

    assert widget.table_logs.rowCount() > 0
    assert TEST_TEXT in message


def test_search(loggerbot):
    qtbot, widget = loggerbot
    qtbot.keyClicks(widget.text_search, TEST_TEXT)

    assert widget.table_logs.isRowHidden(1)

    qtbot.keyClicks(widget.text_search, 'spam!')

    assert widget.table_logs.isRowHidden(0)
    assert widget.table_logs.isRowHidden(1)


def test_copy(loggerbot):
    from qtpy.QtWidgets import QApplication
    app = QApplication.instance()
    qtbot, widget = loggerbot
    qtbot.mouseClick(widget.button_copy, Qt.LeftButton)
    clipped = app.clipboard().text()

    assert TEST_TEXT in clipped
