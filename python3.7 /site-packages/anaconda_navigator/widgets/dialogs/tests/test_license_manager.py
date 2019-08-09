# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Tests for the license manager dialog."""

# yapf: disable

# Third party imports
from qtpy.QtCore import QMimeData, Qt, QTimer, QUrl
from qtpy.QtGui import (QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent,
                        QDropEvent)
from qtpy.QtWidgets import QPushButton
import pytest

# Local imports
from anaconda_navigator.api.anaconda_api import AnacondaAPI
from anaconda_navigator.widgets.dialogs.license import LicenseManagerDialog
import anaconda_navigator.widgets.dialogs.license as license_mod
import anaconda_navigator.widgets.dialogs.tests.data as data


# yapf: enable

EXPIRED_LICENSE_PATH = data.EXPIRED_LICENSE_PATH
INVALID_LICENSE_PATH = data.INVALID_LICENSE_PATH


# --- Helpers
# -----------------------------------------------------------------------------
class MockGetOpenFileName:
    """Mock of the QtPy getopenfilename compatibility function."""

    def __init__(self, path, selected_filter=None):
        self.path = path
        self.selected_filter = selected_filter

    def __call__(self, *args, **kwargs):
        return self.path, self.selected_filter


def create_event(widget, mime_data, event_type):
    """Emulate a event on widget of type drag/drop/move etc."""
    action = Qt.CopyAction | Qt.MoveAction
    point = widget.rect().center()
    event = event_type(point, action, mime_data, Qt.LeftButton, Qt.NoModifier)
    event.acceptProposedAction()
    return event


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def botlicensefilled(qtbot):
    # First remove all licenses
    api = AnacondaAPI()
    api.remove_all_licenses()
    widget = LicenseManagerDialog()
    qtbot.addWidget(widget)
    widget.show()
    widget.add_license(path=EXPIRED_LICENSE_PATH)
    with qtbot.waitSignal(signal=widget.accepted, timeout=1000, raising=False):
        pass
    return qtbot, widget


@pytest.fixture
def botlicense(qtbot):
    # First remove all licenses
    api = AnacondaAPI()
    api.remove_all_licenses()
    widget = LicenseManagerDialog()
    qtbot.addWidget(widget)
    widget.show()
    return qtbot, widget


# --- Tests
# -----------------------------------------------------------------------------
#def test_contact(botlicense):
#    qtbot, widget = botlicense
#    with qtbot.waitSignal(
#        signal=widget.sig_url_clicked, timeout=2000, raising=True
#    ):
#        qtbot.mouseClick(widget.button_contact, Qt.LeftButton)
#
#
#def test_lclose(botlicense):
#    qtbot, widget = botlicense
#    with qtbot.waitSignal(signal=widget.accepted, timeout=5000, raising=True):
#        qtbot.mouseClick(widget.button_ok, Qt.LeftButton)
#
#
#def test_add(botlicense):
#    qtbot, widget = botlicense
#    widget.add_license(path=EXPIRED_LICENSE_PATH)
#    with qtbot.waitSignal(signal=widget.accepted, timeout=1000, raising=False):
#        pass
#    assert bool(widget.count())
#    assert widget.count() == 5
#
#
#def test_add_dialog(botlicense):
#    getopenfilename_original = license_mod.getopenfilename
#    license_mod.getopenfilename = MockGetOpenFileName(EXPIRED_LICENSE_PATH)
#    qtbot, widget = botlicense
#    widget.add_license(path=None)
#
#    with qtbot.waitSignal(signal=widget.accepted, timeout=1000, raising=False):
#        pass
#    assert bool(widget.count())
#    assert widget.count() == 5
#    license_mod.getopenfilename = getopenfilename_original
#
#
#def test_add_dialog_2(botlicense):
#    getopenfilename_original = license_mod.getopenfilename
#    license_mod.getopenfilename = MockGetOpenFileName('')
#    qtbot, widget = botlicense
#    widget.add_license()
#
#    with qtbot.waitSignal(signal=widget.accepted, timeout=1000, raising=False):
#        pass
#    assert not bool(widget.count())
#    assert widget.count() == 0
#    license_mod.getopenfilename = getopenfilename_original
#
#
#def test_add_dialog_invalid(botlicense):
#    getopenfilename_original = license_mod.getopenfilename
#    license_mod.getopenfilename = MockGetOpenFileName(INVALID_LICENSE_PATH)
#    qtbot, widget = botlicense
#
#    def interact():
#        widget.message_box.accept()
#        assert not bool(widget.count())
#        assert widget.count() == 0
#
#    timer = QTimer()
#    timer.singleShot(2000, interact)
#    timer.start()
#    widget.add_license(path=None)
#    license_mod.getopenfilename = getopenfilename_original
#
#
#def test_remove_accept(botlicensefilled):
#    qtbot, widget = botlicensefilled
#
#    def interact():
#        qtbot.mouseClick(widget.message_box.button_remove, Qt.LeftButton)
#
#    timer = QTimer()
#    timer.singleShot(1000, interact)
#    timer.start()
#    widget.remove_license(0)
#
#    assert bool(widget.count())
#    assert widget.count() == 4
#
#
#def test_remove_reject(botlicensefilled):
#    qtbot, widget = botlicensefilled
#
#    def interact():
#        qtbot.mouseClick(widget.message_box.button_cancel, Qt.LeftButton)
#
#    timer = QTimer()
#    timer.singleShot(1000, interact)
#    timer.start()
#    widget.remove_license(0)
#
#    assert bool(widget.count())
#    assert widget.count() == 5
#
#
#def test_remove_current(botlicensefilled):
#    qtbot, widget = botlicensefilled
#    widget.table.selectRow(0)
#
#    def interact():
#        qtbot.mouseClick(widget.message_box.button_remove, Qt.LeftButton)
#
#    timer = QTimer()
#    timer.singleShot(1000, interact)
#    timer.start()
#    widget.remove_license(row=None)
#
#    assert bool(widget.count())
#    assert widget.count() == 4
#
#
#def test_add_drop(botlicense):
#    qtbot, dialog = botlicense
#    mime_no_data = QMimeData()
#    mime_data = QMimeData()
#    mime_data.setUrls([QUrl.fromLocalFile(EXPIRED_LICENSE_PATH)])
#
#    event = create_event(dialog.table, mime_data, QDropEvent)
#    dialog.table.dropEvent(event)
#
#    assert bool(dialog.count())
#    assert dialog.count() == 5
#
#    event = create_event(dialog.table, mime_no_data, QDropEvent)
#    dialog.table.dropEvent(event)
#
#    assert bool(dialog.count())
#    assert dialog.count() == 5
#
#
#def test_data_none(botlicense):
#    qtbot, widget = botlicense
#    widget.model.data(None)
#    index = widget.model.index(-1, -1)
#    widget.model.data(index)
#
#
#def test_background_color(botlicensefilled):
#    qtbot, widget = botlicensefilled
#    button = QPushButton()
#    button.show()
#    widget.table.setFocus()
#    widget.table.selectRow(0)
#    button.setFocus()
#    with qtbot.waitSignal(signal=widget.accepted, timeout=1000, raising=False):
#        pass
#
#
#def test_drag_move_events(botlicense):
#    qtbot, dialog = botlicense
#
#    mime_data = QMimeData()
#    mime_no_data = QMimeData()
#    mime_data.setUrls([QUrl.fromLocalFile(EXPIRED_LICENSE_PATH)])
#
#    event = create_event(dialog.table, mime_data, QDragEnterEvent)
#    dialog.table.dragEnterEvent(event)
#
#    event = create_event(dialog.table, mime_no_data, QDragEnterEvent)
#    dialog.table.dragEnterEvent(event)
#
#    event = create_event(dialog.table, mime_data, QDragMoveEvent)
#    dialog.table.dragMoveEvent(event)
#
#    event = create_event(dialog.table, mime_no_data, QDragMoveEvent)
#    dialog.table.dragMoveEvent(event)
#
#    event = QDragLeaveEvent()
#    dialog.table.dragLeaveEvent(event)
