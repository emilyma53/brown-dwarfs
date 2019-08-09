# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Projects Tab."""

# yapf: disable

from __future__ import absolute_import, division, print_function

# Third party imports
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QHBoxLayout, QMenu, QVBoxLayout

# Local imports
from anaconda_navigator.api.anaconda_api import AnacondaAPI
from anaconda_navigator.utils import constants as C
# from anaconda_navigator.utils.logs import logger
from anaconda_navigator.utils.styles import load_style_sheet
from anaconda_navigator.widgets import (ButtonToolNormal,
                                        FrameEnvironmentsList,
                                        FrameEnvironmentsPackages,
                                        FrameTabHeader, WidgetBase)
from anaconda_navigator.widgets.helperwidgets import (ButtonToggleCollapse,
                                                      LineEditSearch)
from anaconda_navigator.widgets.lists.projects import (ListItemEnv,
                                                       ListWidgetEnv)
from anaconda_navigator.widgets.projects import ProjectsWidget


# yapf: enable

# TODO: Have a single ListWidgetBase that incorporates needed and common
# functionality between projects and envs


class ProjectsTab(WidgetBase):
    """Projects management tab."""
    # name, path, sender
    sig_item_selected = Signal(object, object, object)

    sig_create_requested = Signal()
    sig_import_requested = Signal()
    sig_remove_requested = Signal()
    sig_upload_requested = Signal()

    sig_login_requested = Signal()
    sig_ready = Signal()

    #    sig_apps_changed = Signal(str)
    #    sig_apps_updated = Signal()
    #    sig_project_updated = Signal()
    #    sig_status_updated = Signal(str, int, int, int)

    def __init__(self, parent=None):
        super(ProjectsTab, self).__init__(parent)

        # Variables
        self.api = AnacondaAPI()
        self.current_project = None
        self.style_sheet = None
        self.projects = None

        # Widgets
        self.frame_list = FrameEnvironmentsList(self)
        self.frame_widget = FrameEnvironmentsPackages(self)
        self.frame_header_left = FrameTabHeader()
        self.frame_header_right = FrameTabHeader()
        self.button_create = ButtonToolNormal(text="Create")
        self.button_import = ButtonToolNormal(text="Import")
        self.button_remove = ButtonToolNormal(text="Remove")
        self.button_toggle_collapse = ButtonToggleCollapse()
        self.list = ListWidgetEnv()
        self.widget = ProjectsWidget()
        self.menu_list = QMenu()
        self.text_search = LineEditSearch()

        # Widgets setup
        self.frame_list.is_expanded = True
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_search.setPlaceholderText("Search Projects")
        self.button_create.setObjectName("create")
        self.button_import.setObjectName("import")
        self.button_remove.setObjectName("remove")

        # Layouts
        layout_header_left = QVBoxLayout()
        layout_header_left.addWidget(self.text_search)
        self.frame_header_left.setLayout(layout_header_left)

        layout_buttons = QHBoxLayout()
        layout_buttons.addWidget(self.button_create)
        layout_buttons.addWidget(self.button_import)
        layout_buttons.addWidget(self.button_remove)

        layout_list_buttons = QVBoxLayout()
        layout_list_buttons.addWidget(self.frame_header_left)
        layout_list_buttons.addWidget(self.list)
        layout_list_buttons.addLayout(layout_buttons)
        self.frame_list.setLayout(layout_list_buttons)

        layout_widget = QHBoxLayout()
        layout_widget.addWidget(self.widget)
        self.frame_widget.setLayout(layout_widget)

        layout_main = QHBoxLayout()
        layout_main.addWidget(self.frame_list, 10)
        layout_main.addWidget(self.button_toggle_collapse, 1)
        layout_main.addWidget(self.frame_widget, 30)
        self.setLayout(layout_main)

        # Signals
        self.button_toggle_collapse.clicked.connect(self.expand_collapse)
        self.button_create.clicked.connect(self.sig_create_requested)
        self.button_import.clicked.connect(self.sig_import_requested)
        self.button_remove.clicked.connect(self.sig_remove_requested)

        self.list.sig_item_selected.connect(self._item_selected)
        self.text_search.textChanged.connect(self.filter_list)
        self.widget.sig_login_requested.connect(self.sig_login_requested)

        self.refresh()

    # --- Setup methods
    # -------------------------------------------------------------------------

    def setup(self, projects):
        """Setup tab content and populates the list of projects."""
        self.set_projects(projects=projects)

    def set_projects(self, projects, current_project=None):
        """Populate the list of projects."""
        self.projects = projects
        if current_project is None:
            for (proj_path, proj_name) in projects.items():
                current_project = proj_path
                break

        self.list.clear()
        self.current_project = current_project
        selected_item_row = 0
        for i, (proj_path, proj_name) in enumerate(projects.items()):
            item = ListItemEnv(prefix=proj_path, name=proj_name)

            if proj_path == self.current_project:
                selected_item_row = i
            self.list.addItem(item)

        loading = False
        self.list.setCurrentRow(selected_item_row, loading=loading)
        self.set_project_widget(self.current_project)
        self.filter_list()

    def set_project_widget(self, project_path):
        """Set the project widget."""
        if project_path is None:
            # Disabled widget
            pass
        else:
            self.widget.load_project(project_path)
        self.refresh()
        self.sig_ready.emit()

    def before_delete(self):
        """Prerpare widget before delete."""
        self.widget.before_delete()

    def update_brand(self, brand):
        """Update service brand."""
        self.widget.update_brand(brand)

    # --- Common Helpers (# FIXME: factor out to common base widget)
    # -------------------------------------------------------------------------
    def _item_selected(self, item):
        """Callback to emit signal as user selects an item from the list."""
        prefix = item.prefix()
        self.current_project = prefix
        self.set_loading(prefix)
        self.sig_item_selected.emit(item.name, prefix, C.TAB_PROJECTS)

    def add_temporal_item(self, name):
        """Creates a temporal item on list while creation becomes effective."""
        item_names = [item.name for item in self.list.items()]
        item_names.append(name)
        index = list(sorted(item_names)).index(name) + 1
        item = ListItemEnv(name=name)
        self.list.insertItem(index, item)
        self.list.setCurrentRow(index)
        self.list.scrollToItem(item)
        item.set_loading(True)

    def expand_collapse(self):
        """Expand or collapse the list selector."""
        if self.frame_list.is_expanded:
            self.frame_list.hide()
            self.frame_list.is_expanded = False
        else:
            self.frame_list.show()
            self.frame_list.is_expanded = True

    def filter_list(self, text=None):
        """Filter items in list by name."""
        text = self.text_search.text().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(text not in item.name.lower())

            if not item.widget.isVisible():
                item.widget.repaint()

    def ordered_widgets(self, next_widget=None):
        """Return a list of the ordered widgets."""
        ordered_widgets = [self.text_search]
        ordered_widgets += self.list.ordered_widgets()
        ordered_widgets += [
            self.button_create, self.button_import, self.button_remove
        ]
        ordered_widgets += self.widget.ordered_widgets()
        return ordered_widgets

    def refresh(self):
        """Refresh the enabled/disabled status of the widget and subwidgets."""
        projects = self.projects
        active = bool(projects)
        if not active:
            self.widget.clear()
        self.widget.setVisible(active)
        self.button_remove.setEnabled(active)
        self.widget.setEnabled(active)

    def set_loading(self, prefix=None, value=True):
        """Set the item given by `prefix` to loading state."""
        for row, item in enumerate(self.list.items()):
            if item.prefix == prefix:
                item.set_loading(value)
                self.list.setCurrentRow(row)
                break

    def set_widgets_enabled(self, value):
        """Change the enabled status of widgets and subwidgets."""
        self.list.setEnabled(value)
        self.button_create.setEnabled(value)
        self.button_import.setEnabled(value)
        self.button_remove.setEnabled(value)
        self.widget_projects.set_widgets_enabled(value)
        if value:
            self.refresh()

    @staticmethod
    def update_status(action=None, message=None, value=0, max_value=0):
        """Update status bar."""
        # TODO:!

    def update_style_sheet(self, style_sheet=None):
        """Update custom CSS style sheet."""
        if style_sheet is None:
            self.style_sheet = load_style_sheet()
        else:
            self.style_sheet = style_sheet

        self.setStyleSheet(self.style_sheet)


def local_test():  # pragma: no cover
    """Run local test for project tab."""
    from anaconda_navigator.utils.qthelpers import qapplication
    app = qapplication()
    w = ProjectsTab()
    w.update_style_sheet()
    w.showMaximized()
    app.exec_()


if __name__ == "__main__":  # pragma: no cover
    local_test()
