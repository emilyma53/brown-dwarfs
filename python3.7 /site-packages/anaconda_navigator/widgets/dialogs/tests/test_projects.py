# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Tests for project related dialogs."""

# yapf: disable

# Standard library imports
import os

# Third party imports
from qtpy.QtCore import QEvent, Qt
from qtpy.QtGui import QEnterEvent
import pytest

# Local imports
from anaconda_navigator.utils.fixtures import tmpfile, tmpfolder
from anaconda_navigator.widgets.dialogs import projects


# yapf: enable

PROJECTS = {
    'example-project-1': 'example-project-1',
    'example-project-2': 'example-project-1',
    'example-project-3': 'example-project-1',
}
PROBLEMS = ['problem-1', 'problem-2', 'problem-3', 'problem-4']
tmpfile
tmpfolder


# --- Helpers
# -----------------------------------------------------------------------------
class MockGetExistingDirectory:
    """Mock of the QtPy getopenfilename compatibility function."""

    def __init__(self, path):
        self.path = path

    def __call__(self, *args, **kwargs):
        return self.path


class MockGetOpenFileName:
    """Mock of the QtPy getopenfilename compatibility function."""

    def __init__(self, path, selected_filter=None):
        self.path = path
        self.selected_filter = selected_filter

    def __call__(self, *args, **kwargs):
        return self.path, self.selected_filter


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def botcreate(qtbot):
    """Return bot and widget."""
    widget = projects.CreateDialog(projects=PROJECTS)
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


@pytest.fixture
def botimport(qtbot):
    """Return bot and widget."""
    widget = projects.ImportDialog(projects=PROJECTS)
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


@pytest.fixture
def botremove(qtbot):
    """Return bot and widget."""
    widget = projects.RemoveDialog(project='example-project-2')
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


@pytest.fixture
def botprojectpath(qtbot, tmpfolder):
    """Return bot and widget."""
    widget = projects.ProjectsPathDialog(default=tmpfolder)
    widget.show()
    qtbot.addWidget(widget)
    qtbot.folder = tmpfolder
    return qtbot, widget


@pytest.fixture
def botprojectproblems(qtbot, tmpfolder):
    """Return bot and widget."""
    widget = projects.DialogProblems(problems=PROBLEMS)
    widget.show()
    qtbot.addWidget(widget)
    qtbot.folder = tmpfolder
    return qtbot, widget


# --- Tests
# -----------------------------------------------------------------------------
class TestCreateProjectDialog:
    """Test the creat project dialog."""

    def test_valid(self, botcreate):
        bot, dialog = botcreate
        name = 'example-project-4'
        bot.keyClicks(dialog.text_name, ' ' + name + '    @@')
        assert dialog.button_ok.isEnabled()
        assert dialog.name == name

        with bot.waitSignal(dialog.accepted, timeout=5000, raising=True):
            bot.mouseClick(dialog.button_ok, Qt.LeftButton)

    def test_invalid(self, botcreate):
        bot, dialog = botcreate
        name = 'example-project-1'
        bot.keyClicks(dialog.text_name, name)
        assert not dialog.button_ok.isEnabled()
        assert dialog.name == name

        with bot.waitSignal(dialog.rejected, timeout=5000, raising=True):
            bot.mouseClick(dialog.button_cancel, Qt.LeftButton)


class TestImportProjectDialog:
    """Test the creat project dialog."""

    def test_valid_folder(self, botimport, tmpfolder):
        getexistingdirectory_original = projects.getexistingdirectory
        projects.getexistingdirectory = MockGetExistingDirectory(tmpfolder)
        bot, dialog = botimport
        name = 'example-project-4'
        bot.keyClicks(dialog.text_name, ' ' + name + '    @@')
        bot.mouseClick(dialog.button_path, Qt.LeftButton)

        assert dialog.button_ok.isEnabled()
        assert dialog.name == name
        assert dialog.path == tmpfolder

        projects.getexistingdirectory = getexistingdirectory_original

    def test_invalid_folder(self, botimport, tmpfolder):
        folder = os.path.join(tmpfolder, 'spaces    spaces')
        getexistingdirectory_original = projects.getexistingdirectory
        projects.getexistingdirectory = MockGetExistingDirectory(folder)

        bot, dialog = botimport
        name = 'example-project-4'
        bot.keyClicks(dialog.text_name, ' ' + name + '    @@')
        bot.mouseClick(dialog.button_path, Qt.LeftButton)

        assert not dialog.button_ok.isEnabled()
        assert dialog.name == name
        assert dialog.path == folder

        projects.getexistingdirectory = getexistingdirectory_original

    def test_valid_spec(self, botimport, tmpfile):
        getopenfilename_original = projects.getopenfilename
        projects.getopenfilename = MockGetOpenFileName(tmpfile)
        bot, dialog = botimport
        name = 'example-project-4'
        bot.keyClicks(dialog.text_name, ' ' + name + '    @@')
        dialog.radio_spec.setChecked(True)
        bot.mouseClick(dialog.button_path, Qt.LeftButton)

        assert dialog.button_ok.isEnabled()
        assert dialog.name == name
        assert dialog.path == tmpfile

        projects.getopenfilename = getopenfilename_original

    def test_invalid(self, botimport):
        bot, dialog = botimport
        name = 'example-project-1'
        bot.keyClicks(dialog.text_name, name)
        assert not dialog.button_ok.isEnabled()
        assert dialog.name == name

        with bot.waitSignal(dialog.rejected, timeout=5000, raising=True):
            bot.mouseClick(dialog.button_cancel, Qt.LeftButton)

    def test_label_spec_info(self, botimport):
        bot, dialog = botimport
        pos = dialog.label_info.rect().center()
        event = QEnterEvent(pos, pos, pos)
        dialog.label_info.enterEvent(event)
        assert dialog.label_info.dlg.isVisible()
        event = QEvent(QEvent.Leave)
        dialog.label_info.leaveEvent(event)
        assert not dialog.label_info.dlg.isVisible()


class TestRemoveProjectDialog:
    """Test the remove project dialog."""

    def test_ok(self, botremove):
        bot, dialog = botremove
        with bot.waitSignal(dialog.accepted, timeout=5000, raising=True):
            bot.mouseClick(dialog.button_remove, Qt.LeftButton)

    def test_cancel(self, botcreate):
        bot, dialog = botcreate
        with bot.waitSignal(dialog.rejected, timeout=5000, raising=True):
            bot.mouseClick(dialog.button_cancel, Qt.LeftButton)


class TestProjectPathDialog:
    """Test the remove project dialog."""

    def test_accept_spaces(self, botprojectpath, tmpfolder):
        folder = os.path.join(tmpfolder, 'spaces    spaces')
        getexistingdirectory_original = projects.getexistingdirectory
        projects.getexistingdirectory = MockGetExistingDirectory(folder)
        bot, dialog = botprojectpath
        bot.mouseClick(dialog.button_path, Qt.LeftButton)
        bot.mouseClick(dialog.button_ok, Qt.LeftButton)
        assert not dialog.button_ok.isEnabled()
        projects.getexistingdirectory = getexistingdirectory_original

    def test_choose(self, botprojectpath, tmpfolder):
        getexistingdirectory_original = projects.getexistingdirectory
        projects.getexistingdirectory = MockGetExistingDirectory(tmpfolder)

        bot, dialog = botprojectpath
        bot.mouseClick(dialog.button_path, Qt.LeftButton)
        assert dialog.path == tmpfolder
        projects.getexistingdirectory = getexistingdirectory_original

    def test_use_defaults(self, botprojectpath):
        bot, dialog = botprojectpath
        with bot.waitSignal(dialog.accepted, timeout=5000, raising=True):
            bot.mouseClick(dialog.button_default, Qt.LeftButton)
        assert dialog.path == dialog.default


class TestProjectProblemsDialog:
    """Test the project problems dialog."""

    def test_accept(self, botprojectproblems):
        bot, dialog = botprojectproblems
        with bot.waitSignal(dialog.accepted, timeout=5000, raising=True):
            bot.mouseClick(dialog.button_ok, Qt.LeftButton)
        assert dialog.list.count() == len(PROBLEMS)
