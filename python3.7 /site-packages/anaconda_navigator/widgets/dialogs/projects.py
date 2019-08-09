# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Environment creation, import, deletion dialogs."""

# yapf: disable

# Standard library imports
import os
import sys

# Third party imports
from qtpy.compat import getexistingdirectory, getopenfilename
from qtpy.QtCore import QRegExp, Qt
from qtpy.QtGui import QRegExpValidator
from qtpy.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                            QLineEdit, QListWidget, QListWidgetItem,
                            QRadioButton, QVBoxLayout)

# Local imports
from anaconda_navigator.config import DEFAULT_PROJECTS_PATH, HOME_PATH, WIN
from anaconda_navigator.utils.misc import path_is_writable
from anaconda_navigator.utils.styles import load_style_sheet
from anaconda_navigator.widgets import (ButtonDanger, ButtonNormal,
                                        ButtonPrimary, LabelBase,
                                        SpacerHorizontal, SpacerVertical)
from anaconda_navigator.widgets.dialogs import DialogBase


# yapf: enable

RE_PROJECT_NAME = '[A-Za-z0-9-_]{0,100}'


def get_regex_validator():
    """Helper that creates a regex validator."""
    regex = QRegExp(RE_PROJECT_NAME)
    return QRegExpValidator(regex)


class ListWidgetProblems(QListWidget):
    """Anaconda Project problems list widget."""


class CustomToolTip(DialogBase):
    """Dialog a custom tool tip."""

    def __init__(self, tooltip, parent=None):
        """Dialog a custom tool tip."""
        super(CustomToolTip, self).__init__(parent=parent)
        self._parent = parent
        self._tooltip = tooltip
        self.style_sheet = None

        # Widgets
        self._label_tip = LabelBase(tooltip)

        # Widget setup
        self.frame_title_bar.setVisible(False)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowOpacity(0.96)
        self.setModal(False)

        # Layout
        layout = QHBoxLayout()
        layout.addWidget(self._label_tip)
        self.setLayout(layout)


class DialogProblems(DialogBase):
    """Dialog to display anaconda project problems."""

    def __init__(self, parent=None, problems=None):
        """Dialog to display anaconda project problems."""
        # Check arguments: active channels, must be within channels, otherwise
        # just remove that channel from active channels
        super(DialogProblems, self).__init__(parent=parent)
        self._parent = parent
        self._problems = problems
        self.style_sheet = None

        # Widgets
        self.list = ListWidgetProblems(parent=self)
        self.button_ok = ButtonPrimary('Ok')

        # Widget setup
        self.frame_title_bar.setVisible(False)
        self.list.setFrameStyle(QFrame.NoFrame)
        self.list.setFrameShape(QFrame.NoFrame)
        self.list.setWordWrap(True)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setWindowOpacity(0.96)
        self.setModal(False)

        # Layout
        layout_ok = QHBoxLayout()
        layout_ok.addStretch()
        layout_ok.addWidget(self.button_ok)

        layout = QVBoxLayout()
        layout.addWidget(self.list)
        layout.addWidget(SpacerVertical())
        layout.addWidget(SpacerVertical())
        layout.addLayout(layout_ok)
        self.setLayout(layout)

        # Signals
        self.button_ok.clicked.connect(self.accept)
        self.setup()

    # --- Public API
    # -------------------------------------------------------------------------
    def update_style_sheet(self, style_sheet=None):
        """Update custom css style sheets."""
        if style_sheet is None:
            style_sheet = load_style_sheet()
        self.setMinimumWidth(400)
        self.setStyleSheet(style_sheet)

    def setup(self, problems=None):
        """Setup the channels widget."""
        problems = self._problems or problems
        self._problems = problems

        self.list.clear()
        for i, problem in enumerate(problems):
            item = QListWidgetItem('{}. '.format(i + 1) + problem)
            self.list.addItem(item)
        self.update_style_sheet()
        self.list.setStyleSheet(self.style_sheet)


class LabelSpecInfo(LabelBase):
    """Custom label spec info."""

    def __init__(self, *args, **kwargs):
        super(LabelSpecInfo, self).__init__(*args, **kwargs)
        self.dlg = CustomToolTip(
            'Files of type:<ul>'
            '<li>anaconda-project.yml</li>'
            '<li>environment.yml</li>'
            '<li>requirements.txt</li>'
            '</ul>'
        )

    def _pos(self):
        geo_tl = self.geometry().topRight()
        tl = self.parentWidget().mapToGlobal(geo_tl)
        x = tl.x() - self.dlg.width()
        y = tl.y() + self.height()
        self.dlg.move(x, y)

    def enterEvent(self, event):
        """Override Qt method."""
        if not self.dlg.isVisible():
            self.dlg.show()
            self._pos()
            self.dlg.raise_()
        super(LabelSpecInfo, self).enterEvent(event)

    def leaveEvent(self, event):
        """Override Qt method."""
        self.dlg.hide()
        super(LabelSpecInfo, self).leaveEvent(event)


class CreateDialog(DialogBase):
    """Create new project dialog."""

    def __init__(self, parent=None, projects=None):
        """Create new environment dialog."""
        super(CreateDialog, self).__init__(parent=parent)

        self.projects = projects

        # Widgets
        self.label_name = QLabel("Project name")
        self.text_name = QLineEdit()
        self.button_ok = ButtonPrimary('Create')
        self.button_cancel = ButtonNormal('Cancel')

        # Widgets setup
        self.text_name.setPlaceholderText("New project name")
        self.setMinimumWidth(380)
        self.setWindowTitle("Create new project")
        self.text_name.setValidator(get_regex_validator())

        # Layouts
        grid = QGridLayout()
        grid.addWidget(self.label_name, 0, 0)
        grid.addWidget(SpacerHorizontal(), 0, 1)
        grid.addWidget(self.text_name, 0, 2)
        grid.addWidget(SpacerVertical(), 1, 0)

        layout_buttons = QHBoxLayout()
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.button_cancel)
        layout_buttons.addWidget(SpacerHorizontal())
        layout_buttons.addWidget(self.button_ok)

        main_layout = QVBoxLayout()
        main_layout.addLayout(grid)
        main_layout.addWidget(SpacerVertical())
        main_layout.addWidget(SpacerVertical())
        main_layout.addLayout(layout_buttons)

        self.setLayout(main_layout)

        # Signals
        self.button_ok.clicked.connect(self.accept)
        self.button_cancel.clicked.connect(self.reject)
        self.text_name.textChanged.connect(self.refresh)

        # Setup
        self.refresh()

    def refresh(self, text=''):
        """Update status of buttons based on combobox selection."""
        self.button_ok.setDisabled(True)
        text = self.text_name.text().strip()
        if self.projects is not None:
            if is_valid_project_name(text, self.projects):
                self.button_ok.setDisabled(False)
            else:
                self.button_ok.setDisabled(True)

    @property
    def name(self):
        """Return the project name."""
        return self.text_name.text().strip()


class ImportDialog(DialogBase):
    """Import project from folder or specification files."""

    CONDA_ENV_FILES = 'Conda environment files (*.yaml *.yml)'
    CONDA_SPEC_FILES = 'Conda explicit specification files (*.txt)'
    PIP_REQUIREMENT_FILES = 'Pip requirement files (*.txt)'

    def __init__(self, parent=None, projects=None):
        """Import project from folder or environment files."""
        super(ImportDialog, self).__init__(parent=parent)

        self.projects = projects if projects else {}
        self.selected_file_filter = None
        self._path = None

        # Widgets
        self.label_info = LabelSpecInfo('', parent=self)
        self.label_name = QLabel("Project name")
        self.label_path = QLabel("Specification File")
        self.text_name = QLineEdit()
        self.text_path = QLineEdit()
        self.button_path = ButtonNormal("")
        self.radio_folder = QRadioButton('From folder')
        self.radio_spec = QRadioButton('From specification file')
        self.button_cancel = ButtonNormal('Cancel')
        self.button_ok = ButtonPrimary('Import')

        # Widgets setup
        self.button_path.setObjectName('import')
        self.button_ok.setDefault(True)
        self.text_path.setPlaceholderText("File to import from")
        self.text_name.setPlaceholderText("New project name")
        self.setMinimumWidth(380)
        self.setWindowTitle("Import new project")
        self.text_name.setValidator(get_regex_validator())

        # Layouts
        layout_radio = QHBoxLayout()
        layout_radio.addWidget(self.radio_folder)
        layout_radio.addWidget(SpacerHorizontal())
        layout_radio.addWidget(self.radio_spec)

        layout_infile = QHBoxLayout()
        layout_infile.addWidget(self.text_path)
        layout_infile.addWidget(SpacerHorizontal())
        layout_infile.addWidget(self.button_path)

        layout_grid = QGridLayout()
        layout_grid.addWidget(self.label_name, 0, 0, 1, 2)
        layout_grid.addWidget(SpacerHorizontal(), 0, 2)
        layout_grid.addWidget(self.text_name, 0, 3)
        layout_grid.addWidget(SpacerVertical(), 1, 0)
        layout_grid.addWidget(self.label_path, 2, 0)
        layout_grid.addWidget(self.label_info, 2, 1)
        layout_grid.addWidget(SpacerHorizontal(), 2, 2)
        layout_grid.addLayout(layout_infile, 2, 3)

        layout_buttons = QHBoxLayout()
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.button_cancel)
        layout_buttons.addWidget(SpacerHorizontal())
        layout_buttons.addWidget(self.button_ok)

        layout = QVBoxLayout()
        layout.addLayout(layout_radio)
        layout.addWidget(SpacerVertical())
        layout.addLayout(layout_grid)
        layout.addWidget(SpacerVertical())
        layout.addWidget(SpacerVertical())
        layout.addLayout(layout_buttons)

        self.setLayout(layout)

        # Signals
        self.button_ok.clicked.connect(self.accept)
        self.button_cancel.clicked.connect(self.reject)
        self.button_path.clicked.connect(self.choose)
        self.text_path.textChanged.connect(self.refresh)
        self.text_name.textChanged.connect(self.refresh)
        self.radio_folder.toggled.connect(self.refresh)
        self.radio_spec.toggled.connect(self.refresh)

        # Setup
        self.radio_folder.toggle()
        self.refresh()

    def refresh(self, text=''):
        """Update the status of buttons based on radio selection."""
        if self.radio_folder.isChecked():
            self.text_path.setPlaceholderText("Folder to import from")
            self.label_path.setText('Folder')
            self.label_info.setVisible(False)
        else:
            self.label_info.setVisible(True)
            self.label_path.setText('File ')
            self.text_path.setPlaceholderText("File to import from")

        text = self.text_name.text()
        path = self.text_path.text()

        if (text and path and os.path.exists(path) and
                is_valid_project_name(text, self.projects)):
            self.button_ok.setDisabled(False)
            self.button_ok.setDefault(True)
        else:
            self.button_ok.setDisabled(True)
            self.button_cancel.setDefault(True)

    def choose(self):
        """Display file dialog to select environment specification."""
        selected_filter = None
        if self.radio_spec.isChecked():
            path, selected_filter = getopenfilename(
                caption="Import Project",
                basedir=HOME_PATH,
                parent=None,
                filters="{0};;{1};;{2}".format(
                    self.CONDA_ENV_FILES, self.CONDA_SPEC_FILES,
                    self.PIP_REQUIREMENT_FILES
                )
            )
        else:
            path = getexistingdirectory(
                caption="Import Project",
                basedir=HOME_PATH,
                parent=None,
            )

        if path:
            name = self.text_name.text()
            self.selected_file_filter = selected_filter
            self.text_path.setText(path)
            self.refresh(path)
            self.text_name.setText(name)

    @property
    def name(self):
        """Return the project name."""
        return self.text_name.text().strip()

    @property
    def path(self):
        """Return the project path to import (file or folder)."""
        return self.text_path.text()


class RemoveDialog(DialogBase):
    """Remove existing project dialog."""

    def __init__(self, parent=None, project=None):
        """Remove existing project dialog."""
        super(RemoveDialog, self).__init__(parent=parent)

        # Widgets
        self.button_cancel = ButtonNormal('Cancel')
        self.button_remove = ButtonDanger('Remove')
        self.label_project = QLabel(
            'Do you want to remove project '
            '<b>"{0}"</b> and delete all its files?'.format(project)
        )

        # Widgets Setup
        self.setWindowTitle('Remove project')
        self.setMinimumWidth(380)

        # Layouts
        layout_buttons = QHBoxLayout()
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.button_cancel)
        layout_buttons.addWidget(SpacerHorizontal())
        layout_buttons.addWidget(self.button_remove)

        layout = QVBoxLayout()
        layout.addWidget(self.label_project)
        layout.addWidget(SpacerVertical())
        layout.addWidget(SpacerVertical())
        layout.addLayout(layout_buttons)
        self.setLayout(layout)

        # Signals
        self.button_remove.clicked.connect(self.accept)
        self.button_cancel.clicked.connect(self.reject)


class ProjectsPathDialog(DialogBase):
    """Select project path."""

    def __init__(self, parent=None, default=DEFAULT_PROJECTS_PATH):
        """Select project folder."""
        super(ProjectsPathDialog, self).__init__(parent=parent)

        # Widgets
        self.label_description = QLabel(
            "If no path is selected, the default"
            " one will be used."
        )
        self.label_name = QLabel("Select the projects folder to use")
        self.label_path = QLabel("Projects path")
        self.label_info = QLabel('')
        self.text_path = QLineEdit()
        self.button_path = ButtonNormal("")
        self.button_default = ButtonNormal('Use default')
        self.button_ok = ButtonPrimary('Select')

        # Widgets setup
        self.button_path.setObjectName('import')
        self.default = default
        self.text_path.setPlaceholderText("projects folder path")
        self.text_path.setReadOnly(True)
        self.setMinimumWidth(580)
        self.setWindowTitle("Select Projects Path")

        # Layouts
        layout_grid = QGridLayout()
        layout_grid.addWidget(self.label_path, 0, 0)
        layout_grid.addWidget(SpacerHorizontal(), 0, 1)
        layout_grid.addWidget(self.text_path, 0, 2)
        layout_grid.addWidget(SpacerHorizontal(), 0, 3)
        layout_grid.addWidget(self.button_path, 0, 4)
        layout_grid.addWidget(SpacerVertical(), 1, 0, 1, 4)
        layout_grid.addWidget(self.label_info, 2, 2, 1, 2)

        layout_buttons = QHBoxLayout()
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.button_default)
        layout_buttons.addWidget(SpacerHorizontal())
        layout_buttons.addWidget(self.button_ok)

        layout = QVBoxLayout()
        layout.addWidget(self.label_description)
        layout.addWidget(SpacerVertical())
        layout.addLayout(layout_grid)
        layout.addWidget(SpacerVertical())
        layout.addWidget(SpacerVertical())
        layout.addLayout(layout_buttons)
        self.setLayout(layout)

        # Signals
        self.button_ok.clicked.connect(self.accept)
        self.button_default.clicked.connect(self.use_default)
        self.button_path.clicked.connect(self.choose)

        # Setup
        self.refresh()

    @property
    def path(self):
        """Return the folder project path."""
        return self.text_path.text().strip() or self.default

    def use_default(self):
        """Set the default projects path as the folder path to use."""
        self.text_path.setText('')
        self.accept()

    def choose(self):
        """Display directory dialog to select project folder."""
        path = getexistingdirectory(
            caption="Select Projects Folder",
            basedir=self.default,
            parent=self,
        )
        # Enforce the correct slashes.
        # See Issue https://github.com/ContinuumIO/navigator/issues/1164
        if WIN:
            path = path.replace('/', '\\')
        else:
            path = path.replace('\\', '/')

        if path:
            self.text_path.setText(path)
        self.refresh()
        return path

    def is_valid_path(self):
        """Check that entered path is valid."""
        check = False
        error = ''
        path = self.text_path.text().strip()
        if bool(path) and os.path.isdir(path):
            if ' ' in path:
                error = '<b>Please select a path without spaces</b>'
            elif path == HOME_PATH:
                error = (
                    '<b>Please select a path different to the home '
                    'directory.</b>'
                )
            elif not path_is_writable(path):
                error = ('<b>Please select a path that has write access.</b>')
            check = (
                ' ' not in path and path != HOME_PATH
                and path_is_writable(path)
            )
        return check, error

    def refresh(self):
        """Refresh button status based on path."""
        check, error = self.is_valid_path()
        self.button_ok.setEnabled(check)
        if check or not bool(self.text_path.text()):
            self.label_info.setText('<i>Default: {0}</i>'.format(self.default))
        else:
            self.label_info.setText(error)

    def reject(self):
        """Override Qt method."""
        self.use_default()


def is_valid_project_name(project, projects):
    """
    Check that a project has a valid name.

    Windows is not case sensitive.
    """
    RESERVED_PROJECT_NAMES = ['new']
    project_names = projects.values()

    if WIN:  # pragma: no cover unix
        project = project.lower()
        projects = [p.lower() for p in projects]

    return (
        project and project not in project_names
        and project not in RESERVED_PROJECT_NAMES
    )


# --- Local testing
# -----------------------------------------------------------------------------
def local_test():  # pragma: no cover
    """Run local tests."""
    from anaconda_navigator.utils.qthelpers import qapplication

    app = qapplication()
    #    widget_create = CreateDialog(
    #        parent=None, projects=['project1', 'project2']
    #    )
    #    widget_create.show()
    #
    #    widget_import = ImportDialog(
    #        parent=None, projects=['project1', 'project2']
    #    )
    #    widget_import.show()
    #
    #    widget_remove = RemoveDialog(parent=None, project='Test')
    #    widget_remove.show()
    #
    #    problems = ['problem \n\n as ' + str(i) for i in range(100)]
    #    dlg = DialogProblems(parent=None, problems=problems)
    #    dlg.exec_()

    widget_projects_folder = ProjectsPathDialog(parent=None)
    widget_projects_folder.show()

    sys.exit(app.exec_())


if __name__ == '__main__':  # pragma: no cover
    local_test()
