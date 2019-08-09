# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Tests for environments tab."""

# yapf: disable

# Standard library imports
import sys

# Third party imports
from qtpy.QtCore import Qt
import pytest

# Local imports
from anaconda_navigator.api.conda_api import CondaAPI
from anaconda_navigator.utils.fixtures import tmpfile, tmpfolder
from anaconda_navigator.widgets.dialogs import MessageBoxError
from anaconda_navigator.widgets.tabs.environments import EnvironmentsTab


# yapf: enable

tmpfile
tmpfolder
PY3 = sys.version_info >= (3, 4)
xfail = pytest.mark.xfail


@pytest.fixture()
def env_tab(qtbot, tmpfile):
    widget = EnvironmentsTab()
    qtbot.addWidget(widget)
    widget.show()
    widget.setup_tab(metadata={})
    widget.load_environment()

    with qtbot.waitSignal(widget.sig_status_updated) as blocker:
        blocker

    return widget, qtbot, tmpfile


MessageBoxError.exec_ = lambda *args: True


class TestEnvironmentsTab:
    def package_version(self, pkg, name='root'):
        api = CondaAPI()
        return api.package_version(name=name, pkg=pkg, build=True)

    def remove_env(self, widget):
        worker = widget.packages_widget.remove_environment(
            name='navigatortest'
        )
        worker.communicate()  # run create

    @xfail
    def test_bad_create(self, env_tab):  # analysis:ignore
        widget, qtbot, tmpfile = env_tab

        with open(tmpfile, 'w') as f:
            raw = "name: navigatortest\ndependencies:\n- not-real=0.0.0=py36_0"
            f.write(raw)
        worker = widget.packages_widget.import_yaml(
            name="navigatortest", yaml=tmpfile
        )

        with qtbot.waitSignal(widget.sig_error_popped_up, timeout=5000):
            with qtbot.waitSignal(worker.sig_finished, timeout=5000):
                worker.name = "navigatortest"
                worker.sig_finished.connect(widget._environment_created)

    @xfail
    def test_ipython_option(self, env_tab, tmpfolder):
        widget, qtbot, tmpfile = env_tab
        pyver = 'python={0}'.format(self.package_version('python'))

        self.remove_env(widget)
        worker = widget.packages_widget.create_environment(
            name='navigatortest', packages=[pyver]
        )
        worker.name = 'navigatortest'
        worker.communicate()  # run create
        widget._environment_created(worker, "", "")
        widget.menu_list.exec_ = lambda *args: True
        qtbot.mouseClick(
            widget.list_environments.currentItem().button_options,
            Qt.LeftButton
        )
        is_action_enabled = widget.menu_list.actions()[2].isEnabled()
        assert not is_action_enabled

        worker = widget.packages_widget.api.conda_install(
            name='navigatortest', pkgs=['jupyter-core']
        )
        worker.communicate()
        qtbot.mouseClick(
            widget.list_environments.currentItem().button_options,
            Qt.LeftButton
        )
        assert not widget.menu_list.actions()[2].isEnabled()

        worker = widget.packages_widget.api.conda_install(
            name='navigatortest', pkgs=['ipython']
        )
        worker.communicate()
        qtbot.mouseClick(
            widget.list_environments.currentItem().button_options,
            Qt.LeftButton
        )
        assert widget.menu_list.actions()[2].isEnabled()

        worker = widget.packages_widget.remove_environment(
            name='navigatortest'
        )
        worker.communicate()  # run create

        self.remove_env(widget)
