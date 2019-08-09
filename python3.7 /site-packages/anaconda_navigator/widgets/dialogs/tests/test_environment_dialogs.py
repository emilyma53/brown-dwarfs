# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Tests for environment-related dialogs."""

# yapf: disable

# Standard library imports
import os

# Third party imports
from qtpy.QtCore import QPoint, Qt
import pytest
import yaml

# Local imports
from anaconda_navigator.utils.fixtures import tmpfolder
from anaconda_navigator.widgets.dialogs import environment


# yapf: enable

# Contants
tmpfolder
BASE_ENVIRONMENTS = {
    '/usr/anaconda': 'root',
    '/usr/anaconda/envs/test1': 'test1',
    '/usr/anaconda/envs/test2': 'test2',
}
BASE_INFO = {
    '__environments': BASE_ENVIRONMENTS,
    '__envs_dirs_writable': ['/usr/anaconda/envs/'],
}

BASE_DATA = {
    'info': BASE_INFO,
    'processed_info': BASE_INFO,
    'packages': {
        'python': {
            'versions': ['2.7', '3.10', '3.6']
        }
    }
}


# --- Helpers
# -----------------------------------------------------------------------------
class MockGetOpenFilename:
    """Mock of the QtPy getopenfilename compatibility function."""

    def __init__(self, path, selected_filer):
        self.selected_filter = selected_filer
        self.path = path

    def __call__(self, *args, **kwargs):
        return self.path, self.selected_filter


class MockVersionInfo:
    """Mock of the sys.version_infomodule to get fake higher python version."""
    major = '3'
    minor = '7'


class MockSysModule:
    """Mock of the sys module to get a potential higher python version."""
    version_info = MockVersionInfo()


def widget_pos(widget):
    return QPoint(2, widget.height() / 2)


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def tmpyamlfile(tmpfolder):
    """Return a path to a yaml file with dependencies."""
    path = os.path.join(tmpfolder, 'environment.yaml')
    data = {'dependencies': ['python']}
    with open(path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)
    return path


@pytest.fixture
def tmpyamlnamefile(tmpfolder):
    """Return a path to a yaml file with dependencies and environment name."""
    path = os.path.join(tmpfolder, 'environment.yml')
    data = {'name': 'yamltest', 'dependencies': ['python']}
    with open(path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)
    return path


@pytest.fixture
def botremove(qtbot):
    """Return bot and widget."""
    widget = environment.RemoveDialog(name='test', prefix='/usr/anaconda')
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


@pytest.fixture
def botcreate(qtbot):
    """Return bot and widget."""
    environment.sys = MockSysModule()
    widget = environment.CreateDialog()
    widget.setup(None, BASE_DATA, None)
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


@pytest.fixture
def botimport(qtbot):
    """Return bot and widget."""
    widget = environment.ImportDialog()
    widget.setup(None, BASE_DATA, None)
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


@pytest.fixture
def botclone(qtbot):
    """Return bot and widget."""
    widget = environment.CloneDialog(parent=None, clone_from_name='test1')
    widget.setup(None, BASE_DATA, None)
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


@pytest.fixture
def botconflict(qtbot):
    """Return bot and widget."""
    widget = environment.ConflictDialog(
        parent=None, package='conflict-package'
    )
    widget.setup(None, BASE_DATA, None)
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


@pytest.fixture
def botbase(qtbot):
    """Return bot and widget."""
    widget = environment.EnvironmentActionsDialog(parent=None)
    widget.show()
    qtbot.addWidget(widget)
    return qtbot, widget


# --- Tests
# -----------------------------------------------------------------------------
class TestImportEnvironmentDialog:
    """Test the import environment dialog."""

    def test_conda_env_file(self, botimport, tmpyamlfile):
        bot, widget = botimport
        environment.getopenfilename = MockGetOpenFilename(
            path=tmpyamlfile,
            selected_filer=environment.ImportDialog.CONDA_ENV_FILES
        )

        with bot.waitSignal(widget.text_path.textChanged, 1000, raising=True):
            bot.mouseClick(widget.button_path, Qt.LeftButton)

        # Check path was loaded on text box
        assert widget.text_path.text() == tmpyamlfile
        assert not widget.button_ok.isEnabled()

        # Check repeated env name is dissallowed
        for env_prefix, env_name in BASE_ENVIRONMENTS.items():
            widget.text_name.setText(env_name)
            assert not widget.button_ok.isEnabled()

        # Check non repeated env name is allowed
        widget.text_name.setText('testenv')
        assert widget.button_ok.isEnabled()

        # Check accepts
        with bot.waitSignal(widget.accepted, 1000, raising=True):
            bot.mouseClick(widget.button_ok, Qt.LeftButton)

    def test_conda_env_name_file(self, botimport, tmpyamlnamefile):
        bot, widget = botimport
        environment.getopenfilename = MockGetOpenFilename(
            path=tmpyamlnamefile,
            selected_filer=environment.ImportDialog.CONDA_ENV_FILES
        )

        with bot.waitSignal(widget.text_path.textChanged, 1000, raising=True):
            bot.mouseClick(widget.button_path, Qt.LeftButton)

        # Check path AND name was loaded on text box
        assert widget.text_path.text() == tmpyamlnamefile
        assert widget.text_name.text() == 'yamltest'
        assert widget.button_ok.isEnabled()

    def test_conda_env_invalid_file(self, botimport):
        bot, widget = botimport
        environment.getopenfilename = MockGetOpenFilename(
            path='whatever-invalid-path',
            selected_filer=environment.ImportDialog.CONDA_ENV_FILES
        )

        with bot.waitSignal(widget.text_path.textChanged, 1000, raising=True):
            bot.mouseClick(widget.button_path, Qt.LeftButton)

        # Check filled name and invalid path
        widget.text_name.setText('yamltest')
        assert not widget.button_ok.isEnabled()

        # Check cancels
        with bot.waitSignal(widget.rejected, 1000, raising=True):
            bot.mouseClick(widget.button_cancel, Qt.LeftButton)


class TestCreateEnvironmentDialog:
    """Test the create environment dialog."""

    def test_refresh(self, botcreate):
        bot, widget = botcreate
        assert not widget.button_ok.isEnabled()
        bot.keyClicks(widget.text_name, 'some-env-name')
        assert widget.button_ok.isEnabled()
        widget.text_name.setText("")
        bot.keyClicks(widget.text_name, 'test1')
        assert not widget.button_ok.isEnabled()

    def test_py_r(self, botcreate):
        bot, widget = botcreate
        bot.keyClicks(widget.text_name, 'some-env-name')
        assert widget.install_python
        assert not widget.install_r
        bot.mouseClick(
            widget.check_python,
            Qt.LeftButton,
            pos=widget_pos(widget.check_python)
        )
        assert not widget.install_python
        assert not widget.button_ok.isEnabled()
        assert not widget.combo_version.isEnabled()
        bot.mouseClick(
            widget.check_r, Qt.LeftButton, pos=widget_pos(widget.check_r)
        )
        assert widget.install_r
        assert widget.button_ok.isEnabled()

    def test_create(self, botcreate):
        bot, widget = botcreate
        bot.keyClicks(widget.text_name, 'some-env-name')
        with bot.waitSignal(widget.accepted, 1000, raising=True):
            bot.mouseClick(widget.button_ok, Qt.LeftButton)

    def test_cancel(self, botcreate):
        bot, widget = botcreate
        with bot.waitSignal(widget.rejected, 1000, raising=True):
            bot.mouseClick(widget.button_cancel, Qt.LeftButton)


class TestCloneEnvironmentDialog:
    """Test the clone environment dialog."""

    def test_name(self, botclone):
        bot, widget = botclone

        # Check repeated env name is dissallowed
        for env_prefix, env_name in BASE_ENVIRONMENTS.items():
            widget.text_name.setText('')
            bot.keyClicks(widget.text_name, env_name)
            assert not widget.button_ok.isEnabled()

        widget.text_name.setText('')
        bot.keyClicks(widget.text_name, 'validenvname')
        assert widget.button_ok.isEnabled()

    def test_clone(self, botclone):
        bot, widget = botclone
        bot.keyClicks(widget.text_name, 'validenvname')

        with bot.waitSignal(widget.accepted, 1000, raising=True):
            bot.mouseClick(widget.button_ok, Qt.LeftButton)

    def test_cancel(self, botclone):
        bot, widget = botclone

        with bot.waitSignal(widget.rejected, 1000, raising=True):
            bot.mouseClick(widget.button_cancel, Qt.LeftButton)


class TestRemoveEnvironmentDialog:
    """Test the remove environment dialog."""

    def test_remove(self, botremove):
        bot, widget = botremove

        with bot.waitSignal(widget.accepted, 1000, raising=True):
            bot.mouseClick(widget.button_ok, Qt.LeftButton)

    def test_cancel(self, botremove):
        bot, widget = botremove

        with bot.waitSignal(widget.rejected, 1000, raising=True):
            bot.mouseClick(widget.button_cancel, Qt.LeftButton)


class TestEnvironmentConflict:
    def test_name(self, botconflict):
        qtbot, widget = botconflict
        assert widget.name == 'conflict-package'


class TestEnvironmentDialogBase:
    def test_refresh(self, botbase):
        qtbot, widget = botbase
        with pytest.raises(NotImplementedError):
            widget.refresh()

    def test_prefix(self, botbase):
        qtbot, widget = botbase
        assert not widget.prefix
        assert not widget.name
