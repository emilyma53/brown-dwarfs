# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Tests for channels popup."""

# yapf: disable

# Standard library imports
import random

# Third party imports
from qtpy.QtCore import Qt, QTimer
import pytest

# Local imports
from anaconda_navigator.api.anaconda_api import AnacondaAPI
from anaconda_navigator.config import WIN
from anaconda_navigator.utils.fixtures import tmpfile, tmpfolder
from anaconda_navigator.utils.styles import load_style_sheet
from anaconda_navigator.widgets.dialogs.channels import DialogChannels


# yapf: enable

tmpfile
tmpfolder


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture()
def botchannels(qtbot, tmpfile):
    qtbot.api = AnacondaAPI()
    widget = DialogChannels()
    widget.update_style_sheet(load_style_sheet())

    temp_rc_content = """channels:
  - chdoig
  - sean"""

    with open(tmpfile, 'w') as f:
        f.write(temp_rc_content)

    # Mock conda config data
    config_data = {
        'config_sources': {
            tmpfile: {
                'channels': ['chdoig', 'sean']
            }
        }
    }
    api_info = {'conda_url': 'https://conda.beta.anaconda.org'}
    with qtbot.waitSignal(
        signal=widget.sig_setup_ready, timeout=5000, raising=True
    ):
        if random.randint(0, 1):
            widget.setup(None, config_data, None)
            widget.update_api(None, api_info, None)
        else:
            widget.update_api(None, api_info, None)
            widget.setup(None, config_data, None)

    widget.show()
    return qtbot, widget


# --- Tests
# -----------------------------------------------------------------------------
def test_init(botchannels):
    qtbot, widget = botchannels
    assert widget.list.count() == 2


def test_add_defaults(botchannels):
    qtbot, widget = botchannels
    qtbot.mouseClick(widget.button_add, Qt.LeftButton)
    item = widget.list.item(widget.list.count() - 1)
    qtbot.keyClicks(item.text_channel, 'defaults')
    with qtbot.waitSignal(
        signal=widget.sig_check_ready, timeout=5000, raising=True
    ):
        item = widget.list.item(widget.list.count() - 1)
        qtbot.keyClick(item.text_channel, Qt.Key_Enter)
    item = widget.list.item(widget.list.count() - 1)
    qtbot.mouseClick(widget.button_ok, Qt.LeftButton)

    assert item.text_channel.text() == 'defaults'


def test_add_valid_channels(botchannels, tmpfolder):
    qtbot, widget = botchannels
    if WIN:
        file_channel = 'file:///' + tmpfolder.replace('\\', '/')
    else:
        file_channel = 'file://' + tmpfolder

    channels = {
        'goanpeca':
        'goanpeca',
        'https://anaconda.org/sean':
        'https://conda.anaconda.org/sean',
        'https://conda.anaconda.org/chdoig':
        'https://conda.anaconda.org/chdoig',
        file_channel:
        file_channel,
        'https://conda.anaconda.org/goanpeca':
        'https://conda.anaconda.org/goanpeca',
    }
    for channel, channel_text in channels.items():
        qtbot.mouseClick(widget.button_add, Qt.LeftButton)
        item = widget.list.item(widget.list.count() - 1)
        qtbot.keyClicks(item.text_channel, channel)
        with qtbot.waitSignal(
            signal=widget.sig_check_ready, timeout=10000, raising=True
        ):
            count = widget.list.count()
            item = widget.list.item(count - 1)
            widget.list.validate_channel(item)
        item = widget.list.item(widget.list.count() - 1)
        assert item.text_channel.text() == channel_text

    assert widget.list.count() == len(channels) + 2


def test_add_invalid_channel(botchannels):
    qtbot, widget = botchannels
    qtbot.mouseClick(widget.button_add, Qt.LeftButton)
    item = widget.list.item(widget.list.count() - 1)
    qtbot.keyClicks(item.text_channel, 'whatever-invalid-channel')
    with qtbot.waitSignal(
        signal=widget.sig_check_ready, timeout=10000, raising=True
    ):
        item = widget.list.item(widget.list.count() - 1)
        qtbot.keyClick(item.text_channel, Qt.Key_Enter)
    count = widget.list.count()
    item = widget.list.item(count - 1)
    assert item.label_info.isVisible()
    assert not widget.button_ok.isEnabled()
    assert widget.button_cancel.isEnabled()
    assert not widget.button_add.isEnabled()


def test_add_empty_channel(botchannels):
    qtbot, widget = botchannels
    qtbot.mouseClick(widget.button_add, Qt.LeftButton)
    with qtbot.waitSignal(
        signal=widget.sig_check_ready, timeout=10000, raising=True
    ):
        item = widget.list.item(widget.list.count() - 1)
        qtbot.keyClick(item.text_channel, Qt.Key_Enter)
    count = widget.list.count()
    item = widget.list.item(count - 1)
    assert item.label_info.isVisible()
    assert not widget.button_ok.isEnabled()
    assert widget.button_cancel.isEnabled()
    assert not widget.button_add.isEnabled()


def test_add_duplicate_channel(botchannels):
    qtbot, widget = botchannels
    for channel in ['chdoig', 'chdoig']:
        qtbot.mouseClick(widget.button_add, Qt.LeftButton)
        item = widget.list.item(widget.list.count() - 1)
        qtbot.keyClicks(item.text_channel, channel)
        with qtbot.waitSignal(
            signal=widget.sig_check_ready, timeout=10000, raising=True
        ):
            item = widget.list.item(widget.list.count() - 1)
            qtbot.keyClick(item.text_channel, Qt.Key_Enter)
    count = widget.list.count()
    item = widget.list.item(count - 1)
    assert item.label_info.isVisible()
    assert not widget.button_ok.isEnabled()
    assert widget.button_cancel.isEnabled()
    assert not widget.button_add.isEnabled()


@pytest.mark.skipif(WIN, reason="Fails on appveyor")
def test_remove_button_focus_signal(botchannels):
    qtbot, widget = botchannels
    assert widget.list.currentRow() == -1
    with qtbot.waitSignal(
        signal=widget.list.sig_focus_fixed, timeout=10000, raising=True
    ):
        qtbot.keyClick(widget, Qt.Key_Tab)
    assert widget.list.currentRow() == 0

    with qtbot.waitSignal(
        signal=widget.list.sig_focus_fixed, timeout=10000, raising=True
    ):
        qtbot.keyClick(widget, Qt.Key_Tab)
    assert widget.list.currentRow() == 1


def test_escape_pressed(botchannels):
    qtbot, widget = botchannels
    qtbot.mouseClick(widget.button_add, Qt.LeftButton)
    item = widget.list.item(widget.list.count() - 1)
    qtbot.keyClicks(item.text_channel, 'invalid-channel-name')
    with qtbot.waitSignal(
        signal=widget.sig_check_ready, timeout=10000, raising=True
    ):
        item = widget.list.item(widget.list.count() - 1)
        qtbot.keyClick(item.text_channel, Qt.Key_Enter)
        count = widget.list.count()
        item = widget.list.item(count - 1)
        assert count == 3
        assert item.label_info.isVisible()

    item = widget.list.item(widget.list.count() - 1)
    qtbot.keyClick(item.text_channel, Qt.Key_Escape)
    assert widget.list.count() == 2


def test_menu_copy(botchannels):
    from qtpy.QtCore import QCoreApplication
    app = QCoreApplication.instance()
    qtbot, widget = botchannels
    item = widget.list.item(0)

    def _triggered():
        with qtbot.waitSignal(
            signal=item.text_channel.sig_copied, timeout=2000, raising=True
        ):
            qtbot.keyClick(item.text_channel.menu, Qt.Key_Down)
            qtbot.keyClick(item.text_channel.menu, Qt.Key_Return)
        assert app.clipboard().text() == 'chdoig'

    timer = QTimer()
    timer.timeout.connect(_triggered)
    timer.setInterval(2000)
    timer.start()
    qtbot.mouseClick(item.text_channel, Qt.RightButton)


def test_paste_channel(botchannels):
    from qtpy.QtCore import QCoreApplication
    app = QCoreApplication.instance()
    qtbot, widget = botchannels
    qtbot.mouseClick(widget.button_add, Qt.LeftButton)
    app.clipboard().setText('Metropolis')
    count = widget.list.count()
    item = widget.list.item(count - 1)
    qtbot.keyClick(item.text_channel, Qt.Key_V, modifier=Qt.ControlModifier)
    assert item.text_channel.text() == 'Metropolis'


def test_edit_buttons_disabled(botchannels):
    qtbot, widget = botchannels
    qtbot.mouseClick(widget.button_add, Qt.LeftButton)
    assert not widget.button_ok.isEnabled()
    assert widget.button_cancel.isEnabled()


def test_empty_list(botchannels):
    qtbot, widget = botchannels

    assert widget.button_ok.isEnabled()
    item = widget.list.item(0)
    qtbot.mouseClick(item.button_remove, Qt.LeftButton)
    assert widget.list.count() == 1

    item = widget.list.item(0)
    qtbot.mouseClick(item.button_remove, Qt.LeftButton)
    assert widget.list.count() == 0
    assert not widget.button_ok.isEnabled()


def test_update_style_sheet(botchannels):
    qtbot, widget = botchannels
    widget.style_sheet = None
    widget.update_style_sheet(load_style_sheet())
    assert widget.style_sheet
    widget.style_sheet = None
    widget.update_style_sheet()
    assert widget.style_sheet


def test_reject(botchannels):
    qtbot, widget = botchannels

    with qtbot.waitSignal(signal=widget.rejected, timeout=2000, raising=True):
        widget.update_channels()


def test_reject_2(botchannels):
    qtbot, widget = botchannels

    with qtbot.waitSignal(signal=widget.rejected, timeout=2000, raising=True):
        qtbot.keyClick(widget, Qt.Key_Escape)
