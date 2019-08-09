# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""
Home Tab.

This widget does not perform the actual actions but it emits signals that
should be connected to the final controller on the main window.
"""

# yapf: disable

from __future__ import absolute_import, division, print_function

# Standard library imports
import sys

# Third party imports
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (QApplication, QHBoxLayout, QLabel, QProgressBar,
                            QVBoxLayout)

# Local imports
from anaconda_navigator.api.anaconda_api import AnacondaAPI
from anaconda_navigator.utils import constants as C
from anaconda_navigator.utils.styles import load_style_sheet
from anaconda_navigator.widgets import (ButtonNormal, ComboBoxBase,
                                        FrameTabContent, FrameTabFooter,
                                        FrameTabHeader, LabelBase,
                                        SpacerHorizontal, WidgetBase)
from anaconda_navigator.widgets.lists.apps import (ListItemApplication,
                                                   ListWidgetApplication)


# yapf: enable


# --- Custom widgets used with CSS styling
# -----------------------------------------------------------------------------
class ButtonHomeRefresh(ButtonNormal):
    """QFrame used for CSS styling refresh button inside the Home Tab."""


class ComboHomeEnvironment(ComboBoxBase):
    """Widget Used for CSS styling."""


class ButtonHomeChannels(ButtonNormal):
    """Widget Used for CSS styling."""


class LabelHome(LabelBase):
    """QLabel used for CSS styling the Home Tab label."""


# --- Main widget
# -----------------------------------------------------------------------------
class HomeTab(WidgetBase):
    """Home applications tab."""
    # name, prefix, sender
    sig_item_selected = Signal(object, object, object)

    # button_widget, sender
    sig_channels_requested = Signal(object, object)

    # application_name, command, prefix, leave_path_alone, sender, non_conda
    sig_launch_action_requested = Signal(
        object, object, bool, object, object, object
    )

    # action, application_name, version, sender, non_conda
    sig_conda_action_requested = Signal(object, object, object, object, object)

    # url
    sig_url_clicked = Signal(object)

    # TODO: Connect these signals to have more granularity
    # [{'name': package_name, 'version': version}...], sender
    sig_install_action_requested = Signal(object, object)
    sig_remove_action_requested = Signal(object, object)

    def __init__(self, parent=None):
        """Home applications tab."""
        super(HomeTab, self).__init__(parent)

        # Variables
        self._parent = parent
        self.api = AnacondaAPI()
        self.applications = None
        self.style_sheet = None
        self.app_timers = None
        self.current_prefix = None

        # Widgets
        self.list = ListWidgetApplication()
        self.button_channels = ButtonHomeChannels('Channels')
        self.button_refresh = ButtonHomeRefresh('Refresh')
        self.combo = ComboHomeEnvironment()
        self.frame_top = FrameTabHeader(self)
        self.frame_body = FrameTabContent(self)
        self.frame_bottom = FrameTabFooter(self)
        self.label_home = LabelHome('Applications on')
        self.label_status_action = QLabel('')
        self.label_status = QLabel('')
        self.progress_bar = QProgressBar()
        self.first_widget = self.combo

        # Widget setup
        self.setObjectName('Tab')
        self.progress_bar.setTextVisible(False)
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # Layout
        layout_top = QHBoxLayout()
        layout_top.addWidget(self.label_home)
        layout_top.addWidget(SpacerHorizontal())
        layout_top.addWidget(self.combo)
        layout_top.addWidget(SpacerHorizontal())
        layout_top.addWidget(self.button_channels)
        layout_top.addWidget(SpacerHorizontal())
        layout_top.addStretch()
        layout_top.addWidget(self.button_refresh)
        self.frame_top.setLayout(layout_top)

        layout_body = QVBoxLayout()
        layout_body.addWidget(self.list)
        self.frame_body.setLayout(layout_body)

        layout_bottom = QHBoxLayout()
        layout_bottom.addWidget(self.label_status_action)
        layout_bottom.addWidget(SpacerHorizontal())
        layout_bottom.addWidget(self.label_status)
        layout_bottom.addStretch()
        layout_bottom.addWidget(self.progress_bar)
        self.frame_bottom.setLayout(layout_bottom)

        layout = QVBoxLayout()
        layout.addWidget(self.frame_top)
        layout.addWidget(self.frame_body)
        layout.addWidget(self.frame_bottom)
        self.setLayout(layout)

        # Signals
        self.list.sig_conda_action_requested.connect(
            self.sig_conda_action_requested
        )
        self.list.sig_url_clicked.connect(self.sig_url_clicked)
        self.list.sig_launch_action_requested.connect(
            self.sig_launch_action_requested
        )
        self.button_channels.clicked.connect(self.show_channels)
        self.button_refresh.clicked.connect(self.refresh_cards)
        self.progress_bar.setVisible(False)

    # --- Setup methods
    # -------------------------------------------------------------------------
    def setup(self, conda_data):
        """Setup the tab content."""
        conda_processed_info = conda_data.get('processed_info')
        environments = conda_processed_info.get('__environments')
        applications = conda_data.get('applications')
        packages = conda_data.get('packages')
        self.current_prefix = conda_processed_info.get('default_prefix')
        self.set_environments(environments)
        self.set_applications(applications, packages)

    def set_environments(self, environments):
        """Setup the environments list."""
        # Disconnect to avoid triggering the signal when updating the content
        try:
            self.combo.currentIndexChanged.disconnect()
        except TypeError:
            pass

        self.combo.clear()

        fm = self.combo.fontMetrics()
        widths = []

        for i, (env_prefix, env_name) in enumerate(environments.items()):
            widths.append(fm.width(env_name))
            self.combo.addItem(env_name, env_prefix)
            self.combo.setItemData(i, env_prefix, Qt.ToolTipRole)

        index = 0
        for i, (env_prefix, env_name) in enumerate(environments.items()):
            if self.current_prefix == env_prefix:
                index = i
                break

        self.combo.setCurrentIndex(index)
        self.combo.currentIndexChanged.connect(self._item_selected)

        # Fix combobox width
        width = max(widths) + 64
        self.combo.setMinimumWidth(width)

    def set_applications(self, applications, packages):
        """Build the list of applications present in the current conda env."""
        apps = self.api.process_apps(applications, prefix=self.current_prefix)
        all_applications = []
        installed_applications = []
        not_installed_applications = []

        # Check if some installed applications are not on the apps dict
        # for example when the channel was removed.
        linked_apps = self.api.conda_linked_apps_info(self.current_prefix)
        missing_apps = [app for app in linked_apps if app not in apps]
        for app in missing_apps:
            apps[app] = linked_apps[app]

        for app_name in sorted(list(apps.keys())):
            app = apps[app_name]
            name = app.get('name')
            display_name = app.get('display_name', name)
            package_data = packages.get(app_name) or {}
            description = app['description'] or package_data.get('summary')
            item = ListItemApplication(
                name=name,
                display_name=display_name,
                description=description,
                versions=app['versions'],
                command=app['command'],
                image_path=app['image_path'],
                prefix=self.current_prefix,
                needs_license=app.get('needs_license', False),
                non_conda=app.get('non_conda', False),
            )
            if item.installed:
                installed_applications.append(item)
            else:
                not_installed_applications.append(item)

        all_applications = installed_applications + not_installed_applications

        self.list.clear()
        for i in all_applications:
            self.list.addItem(i)
        self.list.update_style_sheet(self.style_sheet)

        self.set_widgets_enabled(True)
        self.update_status()

    # --- Other methods
    # -------------------------------------------------------------------------
    def current_environment(self):
        """Return the current selected environment."""
        env_name = self.combo.currentText()
        return self.api.conda_get_prefix_envname(env_name)

    def refresh_cards(self):
        """Refresh application widgets.

        List widget items sometimes are hidden on resize. This method tries
        to compensate for that refreshing and repainting on user demand.
        """
        self.list.update_style_sheet(self.style_sheet)
        self.list.repaint()
        for item in self.list.items():
            if not item.widget.isVisible():
                item.widget.repaint()

    def show_channels(self):
        """Emit signal requesting the channels dialog editor."""
        self.sig_channels_requested.emit(self.button_channels, C.TAB_HOME)

    def update_list(self, name=None, version=None):
        """Update applications list."""
        self.set_applications()
        self.label_status.setVisible(False)
        self.label_status_action.setVisible(False)
        self.progress_bar.setVisible(False)

    def update_versions(self, apps=None):
        """Update applications versions."""
        self.items = []

        for i in range(self.list.count()):
            item = self.list.item(i)
            self.items.append(item)
            if isinstance(item, ListItemApplication):
                name = item.name
                meta = apps.get(name)
                if meta:
                    versions = meta['versions']
                    version = self.api.get_dev_tool_version(item.path)
                    item.update_versions(version, versions)

    # --- Common Helpers (# FIXME: factor out to common base widget)
    # -------------------------------------------------------------------------
    def _item_selected(self, index):
        """Notify that the item in combo (environment) changed."""
        name = self.combo.itemText(index)
        prefix = self.combo.itemData(index)
        self.sig_item_selected.emit(name, prefix, C.TAB_HOME)

    @property
    def last_widget(self):
        """Return the last element of the list to be used in tab ordering."""
        if self.list.items():
            return self.list.items()[-1].widget

    def ordered_widgets(self, next_widget=None):
        """Return a list of the ordered widgets."""
        ordered_widgets = [
            self.combo,
            self.button_channels,
            self.button_refresh,
        ]
        ordered_widgets += self.list.ordered_widgets()

        return ordered_widgets

    def set_widgets_enabled(self, value):
        """Enable or disable widgets."""
        self.combo.setEnabled(value)
        self.button_channels.setEnabled(value)
        self.button_refresh.setEnabled(value)
        for item in self.list.items():
            item.button_install.setEnabled(value)
            item.button_options.setEnabled(value)

            if value:
                item.set_loading(not value)

    def update_items(self):
        """Update status of items in list."""
        if self.list:
            for item in self.list.items():
                item.update_status()

    def update_status(self, action='', message='', value=None, max_value=None):
        """Update the application action status."""

        # Elide if too big
        width = QApplication.desktop().availableGeometry().width()
        max_status_length = round(width * (2.0 / 3.0), 0)
        msg_percent = 0.70

        fm = self.label_status_action.fontMetrics()
        action = fm.elidedText(
            action, Qt.ElideRight, round(max_status_length * msg_percent, 0)
        )
        message = fm.elidedText(
            message, Qt.ElideRight,
            round(max_status_length * (1 - msg_percent), 0)
        )
        self.label_status_action.setText(action)
        self.label_status.setText(message)

        if max_value is None and value is None:
            self.progress_bar.setVisible(False)
        else:
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(max_value)
            self.progress_bar.setValue(value)

    def update_style_sheet(self, style_sheet=None):
        """Update custom CSS style sheet."""
        if style_sheet is None:
            self.style_sheet = load_style_sheet()
        else:
            self.style_sheet = style_sheet

        self.list.update_style_sheet(style_sheet=self.style_sheet)
        self.setStyleSheet(self.style_sheet)


# --- Local testing
# -----------------------------------------------------------------------------
def local_test():  # pragma: no cover
    """Run local test."""
    from anaconda_navigator.utils.qthelpers import qapplication

    app = qapplication()
    widget = HomeTab()
    apps = {}
    for i in range(6):
        name = "Package {0}".format(i)
        application = dict(
            name=name,
            prefix='boom',
            description="Scientific PYthon Development EnviRonment",
            versions=[str(i), str(i + 1), str(i + 2)],
            command=None,
            image_path=None
        )
        apps[name] = application
    widget.setup(apps)
    widget.update_style_sheet()
    widget.showMaximized()
    sys.exit(app.exec_())


if __name__ == "__main__":  # pragma: no cover
    local_test()
