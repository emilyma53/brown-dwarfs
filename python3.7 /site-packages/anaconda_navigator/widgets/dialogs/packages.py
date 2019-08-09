# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""About Anaconda Navigator dialog."""

# yapf: disable

# Third party imports
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (QAbstractItemView, QHBoxLayout, QProgressBar,
                            QStackedWidget, QTableWidget, QTableWidgetItem,
                            QTextEdit, QVBoxLayout)

# Local imports
from anaconda_navigator.api.anaconda_api import AnacondaAPI
from anaconda_navigator.utils.styles import load_style_sheet
from anaconda_navigator.widgets import (ButtonNormal, ButtonPrimary, LabelBase,
                                        SpacerHorizontal, SpacerVertical)
from anaconda_navigator.widgets.dialogs import DialogBase


# yapf: enable


class PackagesDialog(DialogBase):
    """Package dependencies dialog."""

    sig_setup_ready = Signal()

    def __init__(
        self,
        parent=None,
        packages=None,
        pip_packages=None,
        remove_only=False,
        update_only=False,
    ):
        """About dialog."""
        super(PackagesDialog, self).__init__(parent=parent)

        # Variables
        self.api = AnacondaAPI()
        self.actions = None
        self.packages = packages or []
        self.pip_packages = pip_packages or []

        # Widgets
        self.stack = QStackedWidget()
        self.table = QTableWidget()
        self.text = QTextEdit()
        self.label_description = LabelBase()
        self.label_status = LabelBase()
        self.progress_bar = QProgressBar()
        self.button_ok = ButtonPrimary('Apply')
        self.button_cancel = ButtonNormal('Cancel')

        # Widget setup
        self.text.setReadOnly(True)
        self.stack.addWidget(self.table)
        self.stack.addWidget(self.text)
        if remove_only:
            text = 'The following packages will be removed:<br>'
        else:
            text = 'The following packages will be modified:<br>'
        self.label_description.setText(text)
        self.label_description.setWordWrap(True)
        self.label_description.setWordWrap(True)
        self.label_status.setWordWrap(True)
        self.table.horizontalScrollBar().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setSortingEnabled(True)
        self._hheader = self.table.horizontalHeader()
        self._vheader = self.table.verticalHeader()
        self._hheader.setStretchLastSection(True)
        self._hheader.setDefaultAlignment(Qt.AlignLeft)
        self._hheader.setSectionResizeMode(self._hheader.Fixed)
        self._vheader.setSectionResizeMode(self._vheader.Fixed)
        self.button_ok.setMinimumWidth(70)
        self.button_ok.setDefault(True)
        self.base_minimum_width = 300 if remove_only else 420
        if remove_only:
            self.setWindowTitle("Remove Packages")
        elif update_only:
            self.setWindowTitle("Update Packages")
        else:
            self.setWindowTitle("Install Packages")

        self.setMinimumWidth(self.base_minimum_width)

        # Layouts
        layout_progress = QHBoxLayout()
        layout_progress.addWidget(self.label_status)
        layout_progress.addWidget(SpacerHorizontal())
        layout_progress.addWidget(self.progress_bar)

        layout_buttons = QHBoxLayout()
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.button_cancel)
        layout_buttons.addWidget(SpacerHorizontal())
        layout_buttons.addWidget(self.button_ok)

        layout = QVBoxLayout()
        layout.addWidget(self.label_description)
        layout.addWidget(SpacerVertical())
        layout.addWidget(self.stack)
        layout.addWidget(SpacerVertical())
        layout.addLayout(layout_progress)
        layout.addWidget(SpacerVertical())
        layout.addWidget(SpacerVertical())
        layout.addLayout(layout_buttons)
        self.setLayout(layout)

        # Signals
        self.button_ok.clicked.connect(self.accept)
        self.button_cancel.clicked.connect(self.reject)
        self.button_ok.setDisabled(True)

        # Setup
        self.table.setDisabled(True)
        self.update_status(
            'Solving package specifications', value=0, max_value=0
        )

    def setup(self, worker, output, error):
        """Setup the widget to include the list of dependencies."""
        if not isinstance(output, dict):
            output = {}

        packages = sorted(pkg.split('==')[0] for pkg in self.packages)
        success = output.get('success')
        error = output.get('error', '')
        exception_name = output.get('exception_name', '')
        actions = output.get('actions', [])
        prefix = worker.prefix

        if exception_name:
            message = exception_name
        else:
            # All requested packages already installed
            message = output.get('message', ' ')

        navi_deps_error = self.api.check_navigator_dependencies(
            actions, prefix
        )
        description = self.label_description.text()

        if error:
            description = 'No packages will be modified.'
            self.stack.setCurrentIndex(1)
            self.button_ok.setDisabled(True)
            if self.api.is_offline():
                error = (
                    "Some of the functionality of Anaconda Navigator "
                    "will be limited in <b>offline mode</b>. <br><br>"
                    "Installation and upgrade actions will be subject to "
                    "the packages currently available on your package "
                    "cache."
                )
            self.text.setText(error)
        elif navi_deps_error:
            description = 'No packages will be modified.'
            error = (
                'Downgrading/removing these packages will modify '
                'Anaconda Navigator dependencies.'
            )
            self.text.setText(error)
            self.stack.setCurrentIndex(1)
            message = 'NavigatorDependenciesError'
            self.button_ok.setDisabled(True)
        elif success and actions:
            self.stack.setCurrentIndex(0)
            # Conda 4.3.x
            if isinstance(actions, list):
                actions_link = actions[0].get('LINK', [])
                actions_unlink = actions[0].get('UNLINK', [])
            # Conda 4.4.x
            else:
                actions_link = actions.get('LINK', [])
                actions_unlink = actions.get('UNLINK', [])

            deps = set()
            deps = deps.union({p['name'] for p in actions_link})
            deps = deps.union({p['name'] for p in actions_unlink})
            deps = deps - set(packages)
            deps = sorted(list(deps))

            count_total_packages = len(packages) + len(deps)
            plural_total = 's' if count_total_packages != 1 else ''
            plural_selected = 's' if len(packages) != 1 else ''

            self.table.setRowCount(count_total_packages)
            self.table.setColumnCount(4)
            if actions_link:
                description = '{0} package{1} will be installed'.format(
                    count_total_packages, plural_total
                )
                self.table.showColumn(2)
                self.table.showColumn(3)
            elif actions_unlink and not actions_link:
                self.table.hideColumn(2)
                self.table.hideColumn(3)
                self.table.setHorizontalHeaderLabels(
                    ['Name', 'Unlink', 'Link', 'Channel']
                )
                description = '{0} package{1} will be removed'.format(
                    count_total_packages, plural_total
                )

            for row, pkg in enumerate(packages + deps):
                link_item = [p for p in actions_link if p['name'] == pkg]
                if not link_item:
                    link_item = {
                        'version': '-'.center(len('link')),
                        'channel': '-'.center(len('channel')),
                    }
                else:
                    link_item = link_item[0]

                unlink_item = [p for p in actions_unlink if p['name'] == pkg]
                if not unlink_item:
                    unlink_item = {
                        'version': '-'.center(len('link')),
                    }
                else:
                    unlink_item = unlink_item[0]

                unlink_version = str(unlink_item['version'])
                link_version = str(link_item['version'])

                item_unlink_v = QTableWidgetItem(unlink_version)
                item_link_v = QTableWidgetItem(link_version)
                item_link_c = QTableWidgetItem(link_item['channel'])
                if pkg in packages:
                    item_name = QTableWidgetItem(pkg)
                else:
                    item_name = QTableWidgetItem('*' + pkg)

                items = [item_name, item_unlink_v, item_link_v, item_link_c]
                for column, item in enumerate(items):
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    self.table.setItem(row, column, item)

            if deps:
                message = (
                    '<b>*</b> indicates the package is a dependency of a '
                    'selected package{0}<br>'
                ).format(plural_selected)

            self.button_ok.setEnabled(True)
            self.table.resizeColumnsToContents()
            unlink_width = self.table.columnWidth(1)
            if unlink_width < 60:
                self.table.setColumnWidth(1, 60)
            self.table.setHorizontalHeaderLabels(
                ['Name  ', 'Unlink  ', 'Link  ', 'Channel  ']
            )

        self.table.setEnabled(True)
        self.update_status(message=message)
        self.label_description.setText(description)

        # Adjust size after data has populated the table
        self.table.resizeColumnsToContents()
        width = sum(
            self.table.columnWidth(i) for i in range(self.table.columnCount())
        )
        delta = (
            self.width() - self.table.width() +
            self.table.verticalHeader().width() + 10
        )

        new_width = width + delta

        if new_width < self.base_minimum_width:
            new_width = self.base_minimum_width

        self.setMinimumWidth(new_width)
        self.setMaximumWidth(new_width)

        self.sig_setup_ready.emit()

    def update_status(self, message='', value=None, max_value=None):
        """Update status of packages dialog."""
        self.label_status.setText(message)

        if max_value is None and value is None:
            self.progress_bar.setVisible(False)
        else:
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(max_value)
            self.progress_bar.setValue(value)


# --- Local testing
# -----------------------------------------------------------------------------
def local_test():  # pragma: no cover
    """Run local test."""
    from anaconda_navigator.utils.qthelpers import qapplication

    app = qapplication()
    widget = PackagesDialog(parent=None)
    widget.setStyleSheet(load_style_sheet())
    widget.show()
    app.exec_()


if __name__ == '__main__':  # pragma: no cover
    local_test()
