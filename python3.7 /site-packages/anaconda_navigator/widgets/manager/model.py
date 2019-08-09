# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Conda Packages Table model."""

# yapf: disable

# Third party imports
from qtpy.QtCore import QAbstractTableModel, QModelIndex, QSize, Qt
from qtpy.QtGui import QColor, QIcon, QPalette

# Local imports
from anaconda_navigator.utils import constants as C
from anaconda_navigator.utils import sort_versions
from anaconda_navigator.utils.styles import MANAGER_TABLE_STYLES


# yapf: enable

GLOBAL_PALLETE = None


def process_pallete():
    """Turn the styles palette into QIcons or QColors for use in the model."""
    global GLOBAL_PALLETE
    if GLOBAL_PALLETE is None:
        GLOBAL_PALLETE = {}
        for key, value in MANAGER_TABLE_STYLES.items():
            if key.startswith('icon.'):
                item = QIcon(value)
            elif key.startswith('color.'):
                item = QColor(value)
            elif key.startswith('size.'):
                item = QSize(*value)
            GLOBAL_PALLETE[key] = item
    return GLOBAL_PALLETE


class CondaPackagesModel(QAbstractTableModel):
    """Abstract Model to handle the packages in a conda environment."""

    def __init__(self, parent, packages, data):
        """Abstract Model to handle the packages in a conda environment."""
        super(CondaPackagesModel, self).__init__(parent)
        self._parent = parent
        self._packages = packages
        self._rows = data
        self._name_to_index = {r[C.COL_NAME]: i for i, r in enumerate(data)}
        self._palette = process_pallete()

    def _update_cell(self, row, column):
        start = self.index(row, column)
        end = self.index(row, column)
        self.dataChanged.emit(start, end)

    @staticmethod
    def flags(index):
        """Override Qt method."""
        column = index.column()

        if index.isValid():
            if column in [C.COL_START, C.COL_END]:
                return Qt.ItemFlags(Qt.ItemIsEnabled)
            else:
                return Qt.ItemFlags(Qt.ItemIsEnabled)
        else:
            return Qt.ItemFlags(Qt.ItemIsEnabled)

    def data(self, index, role=Qt.DisplayRole):
        """Override Qt method."""
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return

        row = index.row()
        column = index.column()

        P = self._palette  # Include the palete directly here.

        if self._rows[row] == row:
            action = C.ACTION_NONE
            type_ = u''
            name = u''
            description = u''
            version = u'-'
            status = -1
        else:
            action = self._rows[row][C.COL_ACTION]
            type_ = self._rows[row][C.COL_PACKAGE_TYPE]
            name = self._rows[row][C.COL_NAME]
            description = self._rows[row][C.COL_DESCRIPTION]
            version = self._rows[row][C.COL_VERSION]
            status = self._rows[row][C.COL_STATUS]

        is_upgradable = self.is_upgradable(self.index(row, C.COL_VERSION))

        if role == Qt.DisplayRole:
            if column == C.COL_PACKAGE_TYPE:
                return type_
            if column == C.COL_NAME:
                return name
            elif column == C.COL_VERSION:
                return version
            elif column == C.COL_STATUS:
                return status
            elif column == C.COL_DESCRIPTION:
                return description
            elif column == C.COL_ACTION:
                return action
        elif role == Qt.TextAlignmentRole:
            if column in [C.COL_NAME, C.COL_DESCRIPTION]:
                return int(Qt.AlignLeft | Qt.AlignVCenter)
            elif column in [C.COL_VERSION]:
                return int(Qt.AlignLeft | Qt.AlignVCenter)
            else:
                return int(Qt.AlignCenter)
        elif role == Qt.DecorationRole:
            if column == C.COL_ACTION:
                if action == C.ACTION_NONE:
                    if status == C.NOT_INSTALLED:
                        return P['icon.action.not_installed']
                    elif status in [C.UPGRADABLE, C.MIXGRADABLE]:
                        return P['icon.action.installed']
                    elif status in [
                        C.INSTALLED, C.DOWNGRADABLE, C.MIXGRADABLE
                    ]:
                        return P['icon.action.installed']
                elif action == C.ACTION_INSTALL:
                    return P['icon.action.add']
                elif action == C.ACTION_REMOVE:
                    return P['icon.action.remove']
                elif action == C.ACTION_UPGRADE:
                    return P['icon.action.upgrade']
                elif action == C.ACTION_UPDATE:
                    return P['icon.action.upgrade']
                elif action == C.ACTION_DOWNGRADE:
                    return P['icon.action.downgrade']
                else:
                    return
            elif column == C.COL_PACKAGE_TYPE:
                if type_ == C.CONDA_PACKAGE:
                    return P['icon.anaconda']
                elif type_ == C.PIP_PACKAGE:
                    return P['icon.python']
                else:
                    return
            elif column == C.COL_VERSION:
                if is_upgradable:
                    return P['icon.upgrade.arrow']
                else:
                    return P['icon.spacer']
        elif role == Qt.ToolTipRole:
            if column == C.COL_PACKAGE_TYPE:
                if type_ == C.CONDA_PACKAGE:
                    return 'Conda package'
                elif type_ == C.PIP_PACKAGE:
                    return 'Python package'
            elif column == C.COL_VERSION and is_upgradable:
                return 'Update available'
        elif role == Qt.ForegroundRole:
            palette = QPalette()
            if column in [C.COL_NAME, C.COL_DESCRIPTION]:
                if status in [
                    C.INSTALLED, C.UPGRADABLE, C.DOWNGRADABLE, C.MIXGRADABLE
                ]:
                    color = palette.color(QPalette.WindowText)
                    color = QColor('#000')
                    return color
                elif status in [C.NOT_INSTALLED]:
                    color = palette.color(QPalette.Mid)
                    color = P['color.foreground.not.installed']
                    return color
            elif column in [C.COL_VERSION] and is_upgradable:
                return P['color.foreground.upgrade']

        elif (role == Qt.SizeHintRole and
              column in [C.ACTION_COLUMNS, C.COL_PACKAGE_TYPE]):
            return P['size.icons']

        return

    @staticmethod
    def headerData(section, orientation, role=Qt.DisplayRole):
        """Override Qt method."""
        if orientation == Qt.Horizontal:
            if role == Qt.TextAlignmentRole:
                return int(Qt.AlignLeft | Qt.AlignVCenter)
            elif role == Qt.ToolTipRole and section == C.COL_PACKAGE_TYPE:
                return 'Package type: Conda, Pip'
            elif role == Qt.DisplayRole:
                if section == C.COL_PACKAGE_TYPE:
                    return "T"
                if section == C.COL_NAME:
                    return "Name"
                elif section == C.COL_VERSION:
                    return "Version"
                elif section == C.COL_DESCRIPTION:
                    return "Description"
                elif section == C.COL_STATUS:
                    return "Status"
                else:
                    return

    def rowCount(self, index=QModelIndex()):
        """Override Qt method."""
        return len(self._rows)

    @staticmethod
    def columnCount(index=QModelIndex()):
        """Override Qt method."""
        return len(C.COLUMNS)

    def row(self, rownum):
        """Return the row data."""
        return self._rows[rownum]

    def first_index(self):
        """Return the first model index."""
        return self.index(0, 0)

    def last_index(self):
        """Return the last model index."""
        return self.index(self.rowCount() - 1, self.columnCount() - 1)

    def update_row_icon(self, row, column):
        """Update the model index icon."""
        if column in C.ACTION_COLUMNS:
            r = self._rows[row]
            actual_state = r[column]
            r[column] = not actual_state
            self._rows[row] = r
            self._update_cell(row, column)

    def is_installable(self, model_index):
        """Return if the pacakge index can be installed."""
        row = model_index.row()
        status = self._rows[row][C.COL_STATUS]
        return status == C.NOT_INSTALLED

    def is_removable(self, model_index):
        """Return if the installed pacakge index can be removed."""
        row = model_index.row()
        status = self._rows[row][C.COL_STATUS]
        return status in [
            C.UPGRADABLE, C.DOWNGRADABLE, C.INSTALLED, C.MIXGRADABLE
        ]

    def is_upgradable(self, model_index):
        """Return if the installed pacakge index can be upgraded."""
        row = model_index.row()
        status = self._rows[row][C.COL_STATUS]
        return status in [C.UPGRADABLE, C.MIXGRADABLE]

    def is_downgradable(self, model_index):
        """Return if the installed pacakge index can be downgraded."""
        row = model_index.row()
        status = self._rows[row][C.COL_STATUS]
        return status in [C.DOWNGRADABLE, C.MIXGRADABLE]

    def action_status(self, model_index):
        """Return the current action status."""
        row = model_index.row()
        action_status = self._rows[row][C.COL_ACTION]
        return action_status

    def set_action_status(self, model_index, status, version=None):
        """Set index status action."""
        row = model_index.row()
        self._rows[row][C.COL_ACTION] = status
        self._rows[row][C.COL_ACTION_VERSION] = version
        self._update_cell(row, model_index.column())

    def clear_actions(self):
        """Clear the selected conda actions."""
        for i, row in enumerate(self._rows):
            self._rows[i][C.COL_ACTION] = C.ACTION_NONE
            self._rows[i][C.COL_ACTION_VERSION] = None
            self._update_cell(i, C.COL_ACTION)
            self._update_cell(i, C.COL_ACTION_VERSION)

    def count_remove_actions(self):
        """Return the number of conda remove actions selected."""
        count = 0
        for i, row in enumerate(self._rows):
            action = self._rows[i][C.COL_ACTION]
            type_ = self._rows[i][C.COL_PACKAGE_TYPE]
            if action == C.ACTION_REMOVE and type_ == C.CONDA_PACKAGE:
                count += 1
        return count

    def count_install_actions(self):
        """Return number of install/upgrade/downgrade actions selected."""
        count = 0
        for i, row in enumerate(self._rows):
            type_ = self._rows[i][C.COL_PACKAGE_TYPE]
            action = self._rows[i][C.COL_ACTION]
            if action in [
                C.ACTION_DOWNGRADE, C.ACTION_INSTALL, C.ACTION_UPGRADE
            ] and type_ == C.CONDA_PACKAGE:
                count += 1
        return count

    def count_update_actions(self):
        """Return number of update (no version given) actions selected."""
        count = 0
        for i, row in enumerate(self._rows):
            type_ = self._rows[i][C.COL_PACKAGE_TYPE]
            action = self._rows[i][C.COL_ACTION]
            if action in [C.ACTION_UPDATE] and type_ == C.CONDA_PACKAGE:
                count += 1
        return count

    def get_actions(self):
        """Return the selected conda actions."""
        dic = {
            C.CONDA_PACKAGE: {
                C.ACTION_INSTALL: [],
                C.ACTION_REMOVE: [],
                C.ACTION_UPGRADE: [],
                C.ACTION_DOWNGRADE: [],
                C.ACTION_UPDATE: [],
            },
            C.PIP_PACKAGE: {
                C.ACTION_REMOVE: [],
            }
        }

        for i, row in enumerate(self._rows):
            action = self._rows[i][C.COL_ACTION]
            name = self._rows[i][C.COL_NAME]
            type_ = self._rows[i][C.COL_PACKAGE_TYPE]
            action_version = self._rows[i][C.COL_ACTION_VERSION]
            current_version = self.get_package_version(name)

            if action != C.ACTION_NONE:
                version_from = current_version
                version_to = action_version
                dic[type_][action].append(
                    {
                        'name': name,
                        'version_from': version_from,
                        'version_to': version_to,
                    }
                )
        return dic

    def get_action_count(self):
        """Count selected actions."""
        count = 0
        for i, row in enumerate(self._rows):
            action = self._rows[i][C.COL_ACTION]

            if action != C.ACTION_NONE:
                count += 1
        return count

    def get_package_versions(self, name):
        """
        Return the package canonical name for a given package `name`.

        name : str
            Name of the package
        """
        package_data = self._packages.get(name)
        versions = []

        if package_data:
            versions = sort_versions(list(package_data.get('versions', [])))

        return versions

    def get_package_version(self, name):
        """Return the package version for a given package `name`."""
        if name in self._name_to_index:
            index = self._name_to_index[name]
            version = self.row(index)[C.COL_VERSION]
            return version.replace(C.UPGRADE_SYMBOL, '')
        else:
            return u''
