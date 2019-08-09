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
from qtpy.compat import getopenfilename
from qtpy.QtCore import QRegExp, Qt, Signal
from qtpy.QtGui import QRegExpValidator
from qtpy.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout
import yaml

# Local imports
from anaconda_navigator.config import (BITS_64, LINUX, MAC, MAC_VERSION_INFO,
                                       WIN)
from anaconda_navigator.widgets import (ButtonDanger, ButtonNormal,
                                        ButtonPrimary, CheckBoxBase,
                                        ComboBoxBase, LabelBase, LineEditBase,
                                        SpacerHorizontal, SpacerVertical)
from anaconda_navigator.widgets.dialogs import DialogBase


# yapf: enable

if WIN:
    REGEX_ENVIRONMENT_NAMES = '^[A-Za-z][A-Za-z0-9_- ]{0,30}$'
else:
    REGEX_ENVIRONMENT_NAMES = '^[A-Za-z][A-Za-z0-9_-]{0,30}$'


class EnvironmentActionsDialog(DialogBase):
    """Base dialog with common methods for all dialogs."""
    BASE_DIALOG_WIDTH = 480
    REGEX_ENV_NAME = REGEX_ENVIRONMENT_NAMES

    sig_setup_ready = Signal()

    def __init__(self, parent=None, api=None):
        """Base dialog with common methods for all dialogs."""
        super(EnvironmentActionsDialog, self).__init__(parent=parent)

        self.info = None
        self.envs_dirs = None
        self.environments = None
        self.api = api
        self.channels = None

        # Widgets to be defined on subcalss __init__
        self.text_name = None
        self.label_prefix = None

    def setup(self, worker=None, conda_data=None, error=None):
        """Setup the dialog conda information as a result of a conda worker."""
        if conda_data:
            conda_info = conda_data.get('processed_info', {})
            self.info = conda_info
            self._packages = conda_data.get('packages')
            self.envs_dirs = conda_info['__envs_dirs_writable']
            self.environments = conda_info['__environments']
            self.channels = conda_info.get('channels')
            self.refresh()
            self.sig_setup_ready.emit()

    def update_location(self):
        """Update the location (prefix) text."""
        self.button_ok.setDisabled(True)
        if self.environments:
            fm = self.label_prefix.fontMetrics()
            prefix = fm.elidedText(self.prefix, Qt.ElideLeft, 300)
            self.label_prefix.setText(prefix)
            self.label_prefix.setToolTip(self.prefix)

    def refresh(self):
        """Update the status of buttons based data entered."""
        self
        raise NotImplementedError

    def is_valid_env_name(self, env_name):
        """
        Check that an environment has a valid name.

        On Windows is case insensitive.
        """
        env_names = self.environments.values() if self.environments else []
        if os.name == 'nt':  # pragma: no cover unix
            env_name = env_name.lower()
            env_names = [e.lower() for e in env_names]

        return env_name and (env_name not in env_names)

    @staticmethod
    def align_labels(widgets):
        """Align label widgets to the right."""
        for widget in widgets:
            widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

    @classmethod
    def get_regex_validator(cls):
        """Helper that creates a regex validator."""
        regex = QRegExp(cls.REGEX_ENV_NAME)
        return QRegExpValidator(regex)

    @property
    def name(self):
        """Return the content without extra spaces for the name of the env."""
        text = ''
        if self.text_name:
            text = self.text_name.text().strip()
        return text

    @property
    def prefix(self):
        """Return the full prefix (location) as entered in the dialog."""
        prefix = ''
        if self.envs_dirs and self.name:
            prefix = os.path.join(self.envs_dirs[0], self.name)
        else:
            prefix = self.name
        return prefix


class CreateDialog(EnvironmentActionsDialog):
    """Create new environment dialog."""

    MRO = 'mro'
    R = 'r'
    PYTHON_VERSIONS = [u'2.7', u'3.5', u'3.6', u'3.7']
    MRO_MAC_MIN_VERSION = (10, 11)

    def __init__(self, parent=None, api=None):
        """Create new environment dialog."""
        super(CreateDialog, self).__init__(parent=parent, api=api)

        # Widgets
        self.label_name = LabelBase("Name:")
        self.label_location = LabelBase("Location:")
        self.label_prefix = LabelBase('')
        self.text_name = LineEditBase()
        self.label_version = LabelBase("Python version")
        self.label_packages = LabelBase("Packages:")
        self.combo_version = ComboBoxBase()
        self.check_python = CheckBoxBase("Python")
        self.check_r = CheckBoxBase('R')
        self.combo_r_type = ComboBoxBase()
        self.button_ok = ButtonPrimary('Create')
        self.button_cancel = ButtonNormal('Cancel')

        # Widgets setup
        self.align_labels(
            [self.label_name, self.label_location, self.label_packages]
        )
        self.text_name.setPlaceholderText("New environment name")
        self.setMinimumWidth(self.BASE_DIALOG_WIDTH)
        self.setWindowTitle("Create new environment")
        self.text_name.setValidator(self.get_regex_validator())
        self.label_prefix.setObjectName('environment-location')
        self.combo_version.setObjectName('package-version')
        self.combo_r_type.setObjectName('r-type')

        # Supported set of python versions
        self.combo_version.setDisabled(True)

        r_types = [self.R]
        self.combo_r_type.clear()
        self.combo_r_type.addItems(r_types)
        self.combo_r_type.setCurrentIndex(0)
        self.combo_r_type.setEnabled(len(r_types) != 1)

        # Layouts
        layout_packages = QGridLayout()
        layout_packages.addWidget(self.check_python, 0, 0)
        layout_packages.addWidget(SpacerHorizontal(), 0, 1)
        layout_packages.addWidget(self.combo_version, 0, 2)
        layout_packages.addWidget(SpacerVertical(), 1, 0)
        layout_packages.addWidget(self.check_r, 2, 0)
        layout_packages.addWidget(SpacerHorizontal(), 2, 1)
        layout_packages.addWidget(self.combo_r_type, 2, 2)

        grid = QGridLayout()
        grid.addWidget(self.label_name, 0, 0, 1, 1)
        grid.addWidget(SpacerHorizontal(), 0, 1, 1, 1)
        grid.addWidget(self.text_name, 0, 2, 1, 4)
        grid.addWidget(SpacerVertical(), 1, 0, 1, 1)
        grid.addWidget(self.label_location, 2, 0, 1, 1)
        grid.addWidget(SpacerHorizontal(), 2, 1, 1, 1)
        grid.addWidget(self.label_prefix, 2, 2, 1, 4)
        grid.addWidget(SpacerVertical(), 3, 0, 1, 1)
        grid.addWidget(self.label_packages, 4, 0, 1, 1)
        grid.addWidget(SpacerHorizontal(), 4, 1, 1, 1)
        grid.addLayout(layout_packages, 4, 2, 3, 1)

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
        self.check_python.stateChanged.connect(self.refresh)
        self.check_r.stateChanged.connect(self.refresh)
        self.sig_setup_ready.connect(self.update_mro)
        self.sig_setup_ready.connect(self.update_pyversions)

        # Setup
        self.text_name.setFocus()
        self.check_python.setChecked(True)
        self.check_r.setChecked(False)
        self.refresh()

    def update_pyversions(self):
        """"""
        python_pks = self._packages.get('python', {})
        python_versions = python_pks.get('versions', [])
        pyvers = set(['.'.join(v.split('.')[:2]) for v in python_versions])

        final_pyvers = []
        for pyver in self.PYTHON_VERSIONS:
            if pyver in pyvers:
                final_pyvers.append(pyver)

        versions = self.PYTHON_VERSIONS
        now = "{}.{}".format(sys.version_info.major, sys.version_info.minor)
        if now not in final_pyvers:
            # Guard against non-standard version, or the coming 3.7
            final_pyvers.append(now)
            final_pyvers.sort()
        final_pyvers = list(reversed(final_pyvers))

        self.combo_version.addItems(final_pyvers)
        self.combo_version.setCurrentIndex(versions.index(now))
        self.combo_version.setEnabled(True)

    def update_mro(self):
        """"""
        # Operating systems with MRO support
        r_types = [self.R]
        if self.api:
            is_mro_available = self.api._conda_api.is_package_available(
                'mro-base',
                channels=self.channels,
            )

            if is_mro_available and BITS_64:
                if ((MAC and MAC_VERSION_INFO > self.MRO_MAC_MIN_VERSION)
                        or WIN or LINUX):
                    r_types = [self.R, self.MRO]

        self.combo_r_type.clear()
        self.combo_r_type.addItems(r_types)
        self.combo_r_type.setCurrentIndex(0)
        self.combo_r_type.setEnabled(len(r_types) != 1)

    def refresh(self, text=''):
        """Update status of buttons based on data."""
        name = self.name
        self.update_location()

        if self.environments:
            check = self.install_python or self.install_r
            if check and self.is_valid_env_name(name):
                self.button_ok.setDisabled(False)
            else:
                self.button_ok.setDisabled(True)
        self.combo_version.setEnabled(self.install_python)
        self.combo_r_type.setEnabled(self.install_r)

    @property
    def python_version(self):
        """Return the python version if python was selected for install."""
        version = None
        if self.install_python:
            version = self.combo_version.currentText()
        return version

    @property
    def install_python(self):
        """Return if python was selected for install."""
        return bool(self.check_python.checkState())

    @property
    def install_r(self):
        """Return if r was selected for install."""
        return bool(self.check_r.checkState())

    @property
    def r_type(self):
        """Return if r was selected for install."""
        return bool(self.combo_r_type.currentText())


class ImportDialog(EnvironmentActionsDialog):
    """Import environment from environment specification dialog."""

    CONDA_ENV_FILES = 'Conda environment files (*.yaml *.yml)'
    CONDA_SPEC_FILES = 'Conda explicit specification files (*.txt)'
    PIP_REQUIREMENT_FILES = 'Pip requirement files (*.txt)'

    def __init__(self, parent=None):
        """Import environment from environment specification dialog."""
        super(ImportDialog, self).__init__(parent=parent)

        self.environments = None
        self.env_dirs = None
        self.selected_file_filter = None

        # Widgets
        self.label_name = LabelBase("Name:")
        self.label_location = LabelBase("Location:")
        self.label_path = LabelBase("Specification File")
        self.text_name = LineEditBase()
        self.label_prefix = LabelBase("")
        self.text_path = LineEditBase()
        self.button_path = ButtonNormal("")
        self.button_cancel = ButtonNormal('Cancel')
        self.button_ok = ButtonPrimary('Import')

        # Widgets setup
        self.align_labels(
            [self.label_name, self.label_location, self.label_path]
        )
        self.label_prefix.setObjectName('environment-location')
        self.button_path.setObjectName('import')
        self.button_ok.setDefault(True)
        self.text_path.setPlaceholderText("File to import from")
        self.text_name.setPlaceholderText("New environment name")
        self.setMinimumWidth(self.BASE_DIALOG_WIDTH)
        self.setWindowTitle("Import new environment")
        self.text_name.setValidator(self.get_regex_validator())

        # Layouts
        layout_infile = QHBoxLayout()
        layout_infile.addWidget(self.text_path)
        layout_infile.addWidget(SpacerHorizontal())
        layout_infile.addWidget(self.button_path)

        layout_grid = QGridLayout()
        layout_grid.addWidget(self.label_name, 0, 0)
        layout_grid.addWidget(SpacerHorizontal(), 0, 1)
        layout_grid.addWidget(self.text_name, 0, 2)
        layout_grid.addWidget(SpacerVertical(), 1, 0)
        layout_grid.addWidget(self.label_location, 2, 0)
        layout_grid.addWidget(SpacerHorizontal(), 2, 1)
        layout_grid.addWidget(self.label_prefix, 2, 2)
        layout_grid.addWidget(SpacerVertical(), 3, 0)
        layout_grid.addWidget(self.label_path, 4, 0)
        layout_grid.addWidget(SpacerHorizontal(), 4, 1)
        layout_grid.addLayout(layout_infile, 4, 2)

        layout_buttons = QHBoxLayout()
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.button_cancel)
        layout_buttons.addWidget(SpacerHorizontal())
        layout_buttons.addWidget(self.button_ok)

        layout = QVBoxLayout()
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

        # Setup
        self.text_name.setFocus()
        self.refresh()

    def choose(self):
        """Display file dialog to select environment specification."""
        path, selected_filter = getopenfilename(
            caption="Import Environment",
            basedir=os.path.expanduser('~'),
            parent=None,
            filters="{0};;{1};;{2}".format(
                self.CONDA_ENV_FILES, self.CONDA_SPEC_FILES,
                self.PIP_REQUIREMENT_FILES
            )
        )

        if path:
            name = self.name
            self.selected_file_filter = selected_filter
            self.text_path.setText(path)
            self.refresh(path)

            # Try to get the name key of the file if an environment.yaml file
            if selected_filter == self.CONDA_ENV_FILES:
                try:
                    with open(path, 'r') as f:
                        raw = f.read()
                    data = yaml.load(raw)
                    name = data.get('name', name)
                except Exception:
                    pass
            self.text_name.setText(name)

    def refresh(self, text=''):
        """Update the status of buttons based data entered."""
        name = self.name
        path = self.path

        self.update_location()

        if (name and path and os.path.exists(self.path) and
                self.is_valid_env_name(name)):
            self.button_ok.setDisabled(False)
            self.button_ok.setDefault(True)
        else:
            self.button_ok.setDisabled(True)
            self.button_cancel.setDefault(True)

    @property
    def path(self):
        """Return the content of the selected path if it exists."""
        path = None
        if os.path.isfile(self.text_path.text()):
            path = self.text_path.text()
        return path


class CloneDialog(EnvironmentActionsDialog):
    """Clone environment dialog."""

    def __init__(self, parent=None, clone_from_name=None):
        """Clone environment dialog."""
        super(CloneDialog, self).__init__(parent=parent)

        # Widgets
        self.label_name = LabelBase("Name:")
        self.text_name = LineEditBase()

        self.label_location = LabelBase("Location:")
        self.label_prefix = LabelBase()
        self.button_ok = ButtonPrimary('Clone')
        self.button_cancel = ButtonNormal('Cancel')

        # Widget setup
        self.align_labels([self.label_name, self.label_location])
        self.setMinimumWidth(self.BASE_DIALOG_WIDTH)
        self.setWindowTitle("Clone from environment: " + clone_from_name)
        self.text_name.setPlaceholderText("New environment name")
        self.text_name.setValidator(self.get_regex_validator())
        self.label_prefix.setObjectName('environment-location')

        # Layouts
        grid = QGridLayout()
        grid.addWidget(self.label_name, 2, 0)
        grid.addWidget(SpacerHorizontal(), 2, 1)
        grid.addWidget(self.text_name, 2, 2)
        grid.addWidget(SpacerVertical(), 3, 0)
        grid.addWidget(self.label_location, 4, 0)
        grid.addWidget(self.label_prefix, 4, 2)

        layout_buttons = QHBoxLayout()
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.button_cancel)
        layout_buttons.addWidget(SpacerHorizontal())
        layout_buttons.addWidget(self.button_ok)

        layout = QVBoxLayout()
        layout.addLayout(grid)
        layout.addWidget(SpacerVertical())
        layout.addWidget(SpacerVertical())
        layout.addLayout(layout_buttons)

        self.setLayout(layout)

        # Signals
        self.text_name.textChanged.connect(self.refresh)
        self.button_ok.clicked.connect(self.accept)
        self.button_cancel.clicked.connect(self.reject)

        # Setup
        self.text_name.setFocus()
        self.refresh()

    def refresh(self, text=''):
        """Update status of buttons based on combobox selection."""
        name = self.name
        self.update_location()
        if self.environments:
            self.button_ok.setDisabled(not self.is_valid_env_name(name))


class RemoveDialog(EnvironmentActionsDialog):
    """Remove existing environment dialog."""

    def __init__(self, parent=None, name=None, prefix=None):
        """Remove existing environment `name` dialog."""
        super(RemoveDialog, self).__init__(parent=parent)

        # Widgets
        self.label_text = LabelBase('Do you want to remove the environment?')
        self.label_name = LabelBase('Name:')
        self.label_name_value = LabelBase(name)
        self.label_location = LabelBase('Location:')
        self.label_prefix = LabelBase(prefix)

        self.button_cancel = ButtonNormal('Cancel')
        self.button_ok = ButtonDanger('Remove')

        # Setup
        self.align_labels([self.label_name, self.label_location])
        self.label_prefix.setObjectName('environment-location')
        self.setWindowTitle('Remove environment')
        self.setMinimumWidth(380)
        self.label_name.setMinimumWidth(60)
        self.label_location.setMinimumWidth(60)

        # Layouts
        layout_name = QHBoxLayout()
        layout_name.addWidget(self.label_name)
        layout_name.addWidget(SpacerHorizontal())
        layout_name.addWidget(self.label_name_value)
        layout_name.addStretch()

        layout_location = QHBoxLayout()
        layout_location.addWidget(self.label_location)
        layout_location.addWidget(SpacerHorizontal())
        layout_location.addWidget(self.label_prefix)
        layout_location.addStretch()

        layout_buttons = QHBoxLayout()
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.button_cancel)
        layout_buttons.addWidget(SpacerHorizontal())
        layout_buttons.addWidget(self.button_ok)

        layout = QVBoxLayout()
        layout.addLayout(layout_name)
        layout.addWidget(SpacerVertical())
        layout.addLayout(layout_location)
        layout.addWidget(SpacerVertical())
        layout.addWidget(SpacerVertical())
        layout.addLayout(layout_buttons)
        self.setLayout(layout)

        # Signals
        self.button_ok.clicked.connect(self.accept)
        self.button_cancel.clicked.connect(self.reject)

        # Setup
        self.update_location()
        self.button_ok.setDisabled(False)


class ConflictDialog(EnvironmentActionsDialog):
    """Create new environment dialog if navigator conflicts with deps."""

    def __init__(
        self, parent=None, package=None, extra_message='', current_prefix=None
    ):
        """Create new environment dialog if navigator conflicts with deps."""
        super(ConflictDialog, self).__init__(parent=parent)

        parts = package.split('=')
        self.package = parts[0] if '=' in package else package
        self.package_version = parts[-1] if '=' in package else ''
        self.current_prefix = current_prefix

        base_message = (
            '<b>{0}</b> cannot be installed on this '
            'environment.'
        ).format(package)

        base_message = extra_message or base_message
        # Widgets
        self.label_info = LabelBase(
            base_message + '<br><br>'
            'Do you want to install the package in an existing '
            'environment or <br>create a new environment?'
            ''.format(package)
        )
        self.label_name = LabelBase('Name:')
        self.label_prefix = LabelBase(' ' * 100)
        self.label_location = LabelBase('Location:')
        self.combo_name = ComboBoxBase()
        self.button_ok = ButtonPrimary('Create')
        self.button_cancel = ButtonNormal('Cancel')

        # Widgets setup
        self.align_labels([self.label_name, self.label_location])
        self.combo_name.setEditable(True)
        self.combo_name.setCompleter(None)
        self.combo_name.setValidator(self.get_regex_validator())
        self.setMinimumWidth(self.BASE_DIALOG_WIDTH)
        self.setWindowTitle("Create new environment for '{}'".format(package))
        self.label_prefix.setObjectName('environment-location')
        self.combo_name.setObjectName('environment-selection')

        # Layouts
        grid_layout = QGridLayout()
        grid_layout.addWidget(self.label_name, 0, 0)
        grid_layout.addWidget(SpacerHorizontal(), 0, 1)
        grid_layout.addWidget(self.combo_name, 0, 2)
        grid_layout.addWidget(SpacerVertical(), 1, 0)
        grid_layout.addWidget(self.label_location, 2, 0)
        grid_layout.addWidget(SpacerHorizontal(), 2, 1)
        grid_layout.addWidget(self.label_prefix, 2, 2)

        layout_buttons = QHBoxLayout()
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.button_cancel)
        layout_buttons.addWidget(SpacerHorizontal())
        layout_buttons.addWidget(self.button_ok)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.label_info)
        main_layout.addWidget(SpacerVertical())
        main_layout.addWidget(SpacerVertical())
        main_layout.addLayout(grid_layout)
        main_layout.addWidget(SpacerVertical())
        main_layout.addWidget(SpacerVertical())
        main_layout.addLayout(layout_buttons)

        self.setLayout(main_layout)

        # Signals
        self.button_ok.clicked.connect(self.accept)
        self.button_cancel.clicked.connect(self.reject)
        self.combo_name.setCurrentText(self.package)
        self.combo_name.currentTextChanged.connect(self.refresh)
        self.button_ok.setDisabled(True)

    def new_env_name(self):
        """Generate a unique environment name."""
        pkg_name_version = self.package + '-' + self.package_version
        if self.environments:
            if self.package not in self.environments.values():
                env_name = self.package
            elif pkg_name_version not in self.environments.values():
                env_name = pkg_name_version
            else:
                for i in range(1, 1000):
                    new_pkg_name = pkg_name_version + '_' + str(i)
                    if new_pkg_name not in self.environments.values():
                        env_name = new_pkg_name
                        break
        else:
            env_name = self.package
        return env_name

    def setup(self, worker, info, error):
        """Setup the dialog conda information as a result of a worker."""
        super(ConflictDialog, self).setup(worker, info, error)
        self.combo_name.blockSignals(True)
        self.combo_name.clear()
        new_env_name = self.new_env_name()
        for i, (env_prefix, env_name) in enumerate(self.environments.items()):
            # Do not include the env where the conflict was found!
            if self.current_prefix != env_prefix:
                self.combo_name.addItem(env_name, env_prefix)
                self.combo_name.setCurrentText(new_env_name)
                self.combo_name.setItemData(i, env_prefix, Qt.ToolTipRole)
        self.combo_name.setCurrentText(new_env_name)
        self.combo_name.blockSignals(False)
        self.refresh()

    def refresh(self):
        """Refresh state of buttons based on content."""
        self.update_location()

        if self.environments:
            self.button_ok.setEnabled(bool(self.name))

    @property
    def name(self):
        """Return the name of the environment."""
        return self.combo_name.currentText()


# --- Local testing
# -----------------------------------------------------------------------------
def local_test():  # pragma: no cover
    """Run local tests."""
    from anaconda_navigator.utils.qthelpers import qapplication
    # from anaconda_navigator.api.anaconda_api import AnacondaAPI

    app = qapplication()

    # api = AnacondaAPI()

    # worker = api.info()
    widget_create = CreateDialog(parent=None)
    # worker.sig_chain_finished.connect(widget_create.setup)
    widget_create.show()

    # worker = api.info()
    # widget_import = ImportDialog(parent=None)
    # worker.sig_chain_finished.connect(widget_import.setup)
    # widget_import.show()

    # worker = api.info()
    # widget_clone = CloneDialog(parent=None, name='root')
    # widget_clone.show()
    # worker.sig_chain_finished.connect(widget_clone.setup)

    # widget_remove = RemoveDialog(
    #     parent=None, name='root', prefix='/User/user/anaconda'
    # )
    # widget_remove.show()

    # worker = api.info()
    # widget_create_conflict = ConflictDialog(
    #     parent=None,
    #     package='orange3',
    # )
    # worker.sig_chain_finished.connect(widget_create_conflict.setup)
    # widget_create_conflict.show()

    app.exec_()


if __name__ == '__main__':  # pragma: no cover
    local_test()
