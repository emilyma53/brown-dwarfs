# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""
Widgets to list applications available to launch from the Home tab.

This widget does not perform the actual conda actions or command launch, but it
emits signals that should be connected to the parents and final controller on
the main window.
"""

# yapf: disable

from __future__ import absolute_import, division, print_function

# Standard library imports
import sys

# Third party imports
from qtpy.QtCore import QPoint, QSize, Qt, QTimer, Signal
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QHBoxLayout, QListWidget, QMenu, QVBoxLayout

# Local imports
from anaconda_navigator.api.anaconda_api import AnacondaAPI
from anaconda_navigator.config import GLOBAL_VSCODE_APP
from anaconda_navigator.static.images import ANACONDA_ICON_256_PATH
from anaconda_navigator.utils import constants as C
from anaconda_navigator.utils.logs import logger
from anaconda_navigator.utils.py3compat import PY3, to_text_string
from anaconda_navigator.utils.qthelpers import (add_actions, create_action,
                                                update_pointer)
from anaconda_navigator.utils.styles import SASS_VARIABLES, load_style_sheet
from anaconda_navigator.widgets import (ButtonLabel, ButtonLink, ButtonNormal,
                                        FrameBase, LabelBase)
from anaconda_navigator.widgets.lists import ListWidgetBase, ListWidgetItemBase
from anaconda_navigator.widgets.spinner import NavigatorSpinner


# yapf: enable


# --- Widgets used in CSS styling
# -----------------------------------------------------------------------------
class ButtonApplicationInstall(ButtonNormal):
    """Button used in CSS styling."""


class ButtonApplicationLaunch(ButtonNormal):
    """Button used in CSS styling."""


class ButtonApplicationOptions(ButtonNormal):
    """Button used in CSS styling."""


class ButtonApplicationUpdate(ButtonNormal):
    """Button used in CSS styling."""


class ButtonApplicationLicense(ButtonLink):
    """Button used in CSS styling."""


class LabelApplicationLicense(ButtonLabel):
    """Button used in CSS styling."""


class LabelApplicationIcon(LabelBase):
    """Label used in CSS styling."""


class LabelApplicationName(LabelBase):
    """Label used in CSS styling."""


class LabelApplicationVersion(LabelBase):
    """Label used in CSS styling."""


class LabelApplicationDescription(LabelBase):
    """Label used in CSS styling."""


class FrameApplicationSpinner(FrameBase):
    """Label used in CSS styling."""


class ButtonApplicationVersion(ButtonLabel):
    """Button used in CSS styling."""


class WidgetApplication(FrameBase):
    """Widget used in CSS styling."""

    # application_name, command, leave_path_alone, prefix, sender, non_conda
    sig_launch_action_requested = Signal(
        object, object, bool, object, object, object
    )

    # action, application_name, version, sender, non_conda
    sig_conda_action_requested = Signal(object, object, object, object, object)

    sig_url_clicked = Signal(object)


# --- Main Widgets
# -----------------------------------------------------------------------------
class ListWidgetApplication(ListWidgetBase):
    """Widget that holds the whole list of applications to launch."""

    # application_name, command, leave_path_alone, prefix, sender, non_conda
    sig_launch_action_requested = Signal(
        object, object, bool, object, object, object
    )

    # action, application_name, version, sender, non_conda
    sig_conda_action_requested = Signal(object, object, object, object, object)

    sig_url_clicked = Signal(object)

    def __init__(self, *args, **kwargs):
        """Widget that holds the whole list of applications to launch."""
        super(ListWidgetApplication, self).__init__(*args, **kwargs)
        self.setGridSize(ListItemApplication.widget_size())
        self.setWrapping(True)
        self.setViewMode(QListWidget.IconMode)
        self.setLayoutMode(ListWidgetApplication.Batched)
        self.setFocusPolicy(Qt.NoFocus)

    def ordered_widgets(self):
        """Return a list of the ordered widgets."""
        ordered_widgets = []
        for item in self.items():
            ordered_widgets += item.ordered_widgets()
        return ordered_widgets

    def setup_item(self, item):
        """Override base method."""
        item.widget.sig_conda_action_requested.connect(
            self.sig_conda_action_requested
        )
        item.widget.sig_launch_action_requested.connect(
            self.sig_launch_action_requested
        )
        item.widget.sig_url_clicked.connect(self.sig_url_clicked)


class ListItemApplication(ListWidgetItemBase):
    """Item with custom widget for the applications list."""

    ICON_SIZE = 64

    def __init__(
        self,
        name=None,
        display_name=None,
        description=None,
        command=None,
        versions=None,
        image_path=None,
        prefix=None,
        needs_license=False,
        non_conda=False,
    ):
        """Item with custom widget for the applications list."""
        super(ListItemApplication, self).__init__()

        self.api = AnacondaAPI()
        self.prefix = prefix
        self.name = name
        self.display_name = display_name if display_name else name
        self.url = ''
        self.expired = False
        self.needs_license = needs_license
        self.description = description
        self.command = command
        self.versions = versions
        self.image_path = image_path if image_path else ANACONDA_ICON_256_PATH
        self.style_sheet = None
        self.timeout = 2000
        self.non_conda = non_conda
        self._vscode_version_value = None

        # Widgets
        self.button_install = ButtonApplicationInstall("Install")  # or Try!
        self.button_launch = ButtonApplicationLaunch("Launch")
        self.button_options = ButtonApplicationOptions()
        self.label_license = LabelApplicationLicense('')
        self.button_license = ButtonApplicationLicense('')
        self.label_icon = LabelApplicationIcon()
        self.label_name = LabelApplicationName(self.display_name)
        self.label_description = LabelApplicationDescription(self.description)
        self.button_version = ButtonApplicationVersion(
            to_text_string(self.version)
        )
        self.menu_options = QMenu('Application options')
        self.menu_versions = QMenu('Install specific version')
        self.pixmap = QPixmap(self.image_path)
        self.timer = QTimer()
        self.widget = WidgetApplication()
        self.frame_spinner = FrameApplicationSpinner()
        self.spinner = NavigatorSpinner(self.widget, total_width=16)
        lay = QHBoxLayout()
        lay.addWidget(self.spinner)
        self.frame_spinner.setLayout(lay)

        # Widget setup
        self.button_version.setFocusPolicy(Qt.NoFocus)
        self.button_version.setEnabled(True)
        self.label_description.setAlignment(Qt.AlignCenter)
        self.timer.setInterval(self.timeout)
        self.timer.setSingleShot(True)
        self.label_icon.setPixmap(self.pixmap)
        self.label_icon.setScaledContents(True)  # important on High DPI!
        self.label_icon.setMaximumWidth(self.ICON_SIZE)
        self.label_icon.setMaximumHeight(self.ICON_SIZE)
        self.label_icon.setAlignment(Qt.AlignCenter)
        self.label_name.setAlignment(Qt.AlignCenter)
        self.label_name.setWordWrap(True)
        self.label_description.setWordWrap(True)
        self.label_description.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.frame_spinner.setVisible(False)

        # Layouts
        layout_spinner = QHBoxLayout()
        layout_spinner.addWidget(self.button_version, 0, Qt.AlignCenter)
        layout_spinner.addWidget(self.frame_spinner, 0, Qt.AlignCenter)

        layout_license = QHBoxLayout()
        layout_license.addStretch()
        layout_license.addWidget(self.label_license, 0, Qt.AlignCenter)
        layout_license.addWidget(self.button_license, 0, Qt.AlignCenter)
        layout_license.addStretch()

        layout_main = QVBoxLayout()
        layout_main.addWidget(self.button_options, 0, Qt.AlignRight)
        layout_main.addWidget(self.label_icon, 0, Qt.AlignCenter)
        layout_main.addWidget(self.label_name, 0, Qt.AlignCenter)
        layout_main.addLayout(layout_spinner)
        layout_main.addLayout(layout_license)
        layout_main.addWidget(self.label_description, 0, Qt.AlignCenter)
        layout_main.addWidget(self.button_launch, 0, Qt.AlignCenter)
        layout_main.addWidget(self.button_install, 0, Qt.AlignCenter)

        self.widget.setLayout(layout_main)
        self.widget.setStyleSheet(load_style_sheet())
        self.setSizeHint(self.widget_size())
        # This might help with visual quirks on the home screen
        self.widget.setMinimumSize(self.widget_size())

        # Signals
        self.button_install.clicked.connect(self.install_application)
        self.button_launch.clicked.connect(self.launch_application)
        self.button_options.clicked.connect(self.actions_menu_requested)
        self.button_license.clicked.connect(self.launch_url)
        self.timer.timeout.connect(self._application_launched)

        # Setup
        self.update_status()

    # --- Callbacks
    # -------------------------------------------------------------------------
    def _application_launched(self):
        self.button_launch.setDisabled(False)
        update_pointer()

    # --- Helpers
    # -------------------------------------------------------------------------
    def update_style_sheet(self, style_sheet=None):
        """Update custom CSS stylesheet."""
        if style_sheet:
            self.style_sheet = style_sheet
        else:
            self.style_sheet = load_style_sheet()

        self.menu_options.setStyleSheet(self.style_sheet)
        self.menu_versions.setStyleSheet(self.style_sheet)

    def ordered_widgets(self):
        """Return a list of the ordered widgets."""
        return [
            self.button_license, self.button_install, self.button_launch,
            self.button_options
        ]

    @staticmethod
    def widget_size():
        """Return the size defined in the SASS file."""
        return QSize(
            SASS_VARIABLES.WIDGET_APPLICATION_TOTAL_WIDTH,
            SASS_VARIABLES.WIDGET_APPLICATION_TOTAL_HEIGHT
        )

    def launch_url(self):
        """Launch signal for url click."""
        self.widget.sig_url_clicked.emit(self.url)

    def actions_menu_requested(self):
        """Create and display menu for the currently selected application."""
        self.menu_options.clear()
        self.menu_versions.clear()

        # Add versions menu
        versions = self.versions if self.versions else []
        version_actions = []
        for version in reversed(versions):
            action = create_action(
                self.widget,
                version,
                triggered=lambda value, version=version: self.
                install_application(version=version)
            )

            action.setCheckable(True)
            if self.version == version and self.installed:
                action.setChecked(True)
                action.setDisabled(True)

            version_actions.append(action)

        install_action = create_action(
            self.widget,
            'Install application',
            triggered=lambda: self.install_application()
        )
        install_action.setEnabled(not self.installed)

        update_action = create_action(
            self.widget,
            'Update application',
            triggered=lambda: self.update_application()
        )

        if versions and versions[-1] == self.version:
            update_action.setDisabled(True)
        else:
            update_action.setDisabled(False)

        if self.non_conda and self.name == GLOBAL_VSCODE_APP:
            update_action.setDisabled(True)

        remove_action = create_action(
            self.widget,
            'Remove application',
            triggered=lambda: self.remove_application()
        )
        remove_action.setEnabled(self.installed)

        actions = [
            install_action, update_action, remove_action, None,
            self.menu_versions
        ]
        add_actions(self.menu_options, actions)
        add_actions(self.menu_versions, version_actions)
        offset = QPoint(self.button_options.width(), 0)
        position = self.button_options.mapToGlobal(QPoint(0, 0))
        self.menu_versions.setEnabled(len(versions) > 1)
        self.menu_options.move(position + offset)
        self.menu_options.exec_()

    def update_status(self):
        """Update status."""
        # License check
        license_label_text = ''
        license_url_text = ''
        self.url = ''
        self.expired = False
        button_label = 'Install'

        if self.needs_license:
            # TODO: Fix this method to use the api
            license_info = self.api.get_package_license(self.name)
            license_days = self.api.get_days_left(license_info)
            end_date = license_info.get('end_date', '')
            self.expired = license_days == 0
            plural = 's' if license_days != 1 else ''
            is_trial = license_info.get('type', '').lower() == 'trial'

            if self.installed and license_info:
                if is_trial and not self.expired:
                    license_label_text = (
                        'Trial, {days} day{plural} '
                        'remaining'.format(days=license_days, plural=plural)
                    )
                    self.url = ''
                elif is_trial and self.expired:
                    license_label_text = 'Trial expired, '
                    license_url_text = 'contact us'
                    self.url = 'mailto:sales@continuum.io'
                elif not is_trial and not self.expired:
                    license_label_text = 'License expires {}'.format(end_date)
                    self.url = ''
                elif not is_trial and self.expired:
                    license_url_text = 'Renew license'
                    self.url = 'mailto:sales@continuum.io'
            elif self.installed and not bool(license_info):
                # Installed but no license found!
                license_url_text = 'No license found'
                self.url = 'mailto:sales@continuum.io'
            else:
                if not self.expired:
                    button_label = 'Install'
                else:
                    button_label = 'Try'

        self.button_license.setText(license_url_text)
        self.button_license.setVisible(bool(self.url))
        self.label_license.setText(license_label_text)
        self.label_license.setVisible(bool(license_label_text))

        # Version and version updates
        if (self.versions and self.version != self.versions[-1] and
                self.installed):
            # The property is used with CSS to display updatable packages.
            self.button_version.setProperty('pressed', True)
            self.button_version.setToolTip(
                'Version {0} available'.format(self.versions[-1])
            )
        else:
            self.button_version.setProperty('pressed', False)

        # For VScode app do not display if new updates are available
        # See: https://github.com/ContinuumIO/navigator/issues/1504
        if self.non_conda and self.name == GLOBAL_VSCODE_APP:
            self.button_version.setProperty('pressed', False)
            self.button_version.setToolTip('')

        if not self.needs_license:
            self.button_install.setText(button_label)
            self.button_install.setVisible(not self.installed)
            self.button_launch.setVisible(self.installed)
        else:
            self.button_install.setText('Try' if self.expired else 'Install')
            self.button_launch.setVisible(not self.expired)
            self.button_install.setVisible(self.expired)

        self.button_launch.setEnabled(True)

    def update_versions(self, version=None, versions=None):
        """Update button visibility depending on update availability."""
        logger.debug(str((self.name, self.dev_tool, self.installed)))

        if self.installed and version:
            self.button_options.setVisible(True)
            self.button_version.setText(version)
            self.button_version.setVisible(True)
        elif not self.installed and versions:
            self.button_install.setEnabled(True)
            self.button_version.setText(versions[-1])
            self.button_version.setVisible(True)

        self.versions = versions
        self.version = version
        self.update_status()

    def set_loading(self, value):
        """Set loading status."""
        self.button_install.setDisabled(value)
        self.button_options.setDisabled(value)
        self.button_launch.setDisabled(value)
        self.button_license.setDisabled(value)

        if value:
            self.spinner.start()
        else:
            self.spinner.stop()
            if self.version is None and self.versions is not None:
                version = self.versions[-1]
            else:
                version = self.version
            self.button_version.setText(version)
            self.button_launch.setDisabled(self.expired)

        self.frame_spinner.setVisible(value)
        self.button_version.setVisible(not value)

    # --- Helpers using api
    # -------------------------------------------------------------------------
    def _vscode_version(self):
        """Query the vscode version for the default installation path."""
        version = None
        if self._vscode_version_value is None:
            exe = self.api.vscode_executable()
            # exe = '"' + exe + '"' if ' ' in exe else exe
            cmd = [exe, '--version']

            import subprocess
            stdout = ''
            stderr = ''
            error = False
            try:
                p = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    executable=exe,
                )
                stdout, stderr = p.communicate()
                if PY3:
                    stdout = stdout.decode()
                    stderr = stderr.decode()
            except OSError as e:
                error = True

            if stdout:
                output = [o for o in stdout.split('\n') if o and '.' in o]
                version = output[0]

            self._vscode_version_value = version
        else:
            version = self._vscode_version_value

        return version

    @property
    def installed(self):
        """Return the installed status of the package."""
        version = None
        if self.non_conda and self.name == GLOBAL_VSCODE_APP:
            # TODO: Vscode program location, check existence
            version = self._vscode_version()
        elif self.prefix:
            version = self.api.conda_package_version(
                prefix=self.prefix, pkg=self.name, build=False
            )
        return bool(version)

    @property
    def version(self):
        """Return the current installed version or the highest version."""
        version = None
        if self.non_conda and self.name == GLOBAL_VSCODE_APP:
            version = self._vscode_version()
        elif self.prefix:
            version = self.api.conda_package_version(
                prefix=self.prefix, pkg=self.name, build=False
            )

        if not version:
            version = self.versions[-1]

        return version

    # --- Application actions
    # ------------------------------------------------------------------------
    def install_application(self, value=None, version=None, install=True):
        """
        Update the application on the defined prefix environment.

        This is used for both normal install and specific version install.
        """
        if not version:
            version = self.versions[-1]

        action = C.APPLICATION_INSTALL if install else C.APPLICATION_UPDATE
        self.widget.sig_conda_action_requested.emit(
            action,
            self.name,
            version,
            C.TAB_HOME,
            self.non_conda,
        )
        self.set_loading(True)

    def remove_application(self):
        """Remove the application from the defined prefix environment."""
        self.widget.sig_conda_action_requested.emit(
            C.APPLICATION_REMOVE,
            self.name,
            None,
            C.TAB_HOME,
            self.non_conda,
        )
        self.set_loading(True)

    def update_application(self):
        """Update the application on the defined prefix environment."""
        self.install_application(version=self.versions[-1], install=False)

    def launch_application(self):
        """Launch application installed in prefix environment."""
        leave_path_alone = False
        if self.command is not None:
            if self.non_conda and self.name == GLOBAL_VSCODE_APP:
                leave_path_alone = True
                # args = [self.command]
                args = [self.api.vscode_executable()]
            else:
                args = self.command.split(' ')
                leave_path_alone = True

            self.button_launch.setDisabled(True)
            self.timer.setInterval(self.timeout)
            self.timer.start()
            update_pointer(Qt.BusyCursor)
            self.widget.sig_launch_action_requested.emit(
                self.name,
                args,
                leave_path_alone,
                self.prefix,
                C.TAB_HOME,
                self.non_conda,
            )


# --- Local testing
# -----------------------------------------------------------------------------
def local_test():  # pragma: no cover
    """Run local test."""
    from anaconda_navigator.utils.qthelpers import qapplication
    from anaconda_navigator.static.images import ANACONDA_ICON_256_PATH

    app = qapplication(test_time=5)
    widget = ListWidgetApplication()
    for i in range(30):
        item = ListItemApplication(
            name="Package {0}".format(i),
            description="Scientific PYthon Development EnviRonment",
            versions=[str(i), str(i + 1)],
            image_path=ANACONDA_ICON_256_PATH,
            prefix=None
        )
        widget.addItem(item)

    widget.update_style_sheet()
    widget.show()
    sys.exit(app.exec_())


if __name__ == "__main__":  # pragma: no cover
    local_test()
