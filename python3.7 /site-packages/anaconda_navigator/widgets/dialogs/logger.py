# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Logger widget."""

# yapf: disable

# Standard library imports
import json
import os
import sys

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QApplication, QHBoxLayout, QHeaderView, QLabel,
                            QTableWidget, QTableWidgetItem, QVBoxLayout)

# Local imports
from anaconda_navigator.config import LOG_FILENAME, LOG_FOLDER
from anaconda_navigator.utils.logs import load_log, log_files
from anaconda_navigator.utils.styles import load_style_sheet
from anaconda_navigator.widgets import (ButtonPrimary, ComboBoxBase,
                                        SpacerHorizontal, SpacerVertical)
from anaconda_navigator.widgets.dialogs import DialogBase
from anaconda_navigator.widgets.helperwidgets import LineEditSearch


# yapf: enable


class LogViewerDialog(DialogBase):
    """Logger widget."""

    def __init__(
        self,
        parent=None,
        log_folder=LOG_FOLDER,
        log_filename=LOG_FILENAME,
    ):
        """
        Logger widget.

        Parameters
        ----------
        log_folder: str
            Folder where logs are located
        log_filename: str
            Basic name for the rotating log files.
        """
        super(LogViewerDialog, self).__init__(parent=parent)

        self._data = None
        self._columns = ['level', 'time', 'module', 'method', 'message']
        self._headers = [c.capitalize() for c in self._columns]
        self._log_filename = log_filename
        self._log_folder = log_folder

        # Widgets
        self.label = QLabel('Select log file:')
        self.combobox = ComboBoxBase()
        self.table_logs = QTableWidget(self)
        self.button_copy = ButtonPrimary('Copy')
        self.text_search = LineEditSearch()

        # Widget setup
        self.table_logs.setAttribute(Qt.WA_LayoutUsesWidgetRect, True)
        horizontal_header = self.table_logs.horizontalHeader()
        vertical_header = self.table_logs.verticalHeader()
        horizontal_header.setStretchLastSection(True)
        horizontal_header.setSectionResizeMode(QHeaderView.Fixed)
        vertical_header.setSectionResizeMode(QHeaderView.Fixed)

        self.table_logs.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_logs.setEditTriggers(QTableWidget.NoEditTriggers)

        self.setWindowTitle('Log Viewer')
        self.setMinimumWidth(800)
        self.setMinimumHeight(500)
        self.text_search.setPlaceholderText("Search...")

        # Layouts
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.label)
        top_layout.addWidget(SpacerHorizontal())
        top_layout.addWidget(self.combobox)
        top_layout.addStretch()
        top_layout.addWidget(SpacerHorizontal())
        top_layout.addWidget(self.text_search)
        top_layout.addWidget(SpacerHorizontal())
        top_layout.addWidget(self.button_copy)
        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addWidget(SpacerVertical())
        layout.addWidget(self.table_logs)
        self.setLayout(layout)

        # Signals
        self.combobox.currentIndexChanged.connect(self.update_text)
        self.button_copy.clicked.connect(self.copy_item)
        self.text_search.textChanged.connect(self.filter_text)

        # Setup()
        self.setup()
        self.update_style_sheet()

    def update_style_sheet(self, style_sheet=None):
        """Update custom CSS stylesheet."""
        if style_sheet is None:
            style_sheet = load_style_sheet()
        self.setStyleSheet(style_sheet)

    def setup(self):
        """Setup widget content."""
        self.combobox.clear()
        paths = log_files(
            log_folder=self._log_folder,
            log_filename=self._log_filename,
        )
        files = [os.path.basename(p) for p in paths]
        self.combobox.addItems(files)

    def filter_text(self):
        """Search for text in the selected log file."""
        search = self.text_search.text().lower()
        for i, data in enumerate(self._data):
            if any(search in str(d).lower() for d in data.values()):
                self.table_logs.showRow(i)
            else:
                self.table_logs.hideRow(i)

    def row_data(self, row):
        """Give the current row data concatenated with spaces."""
        data = {}
        if self._data:
            length = len(self._data)
            if 0 >= row < length:
                data = self._data[row]
        return data

    def update_text(self, index):
        """Update logs based on combobox selection."""
        path = os.path.join(self._log_folder, self.combobox.currentText())
        self._data = load_log(path)

        self.table_logs.clear()
        self.table_logs.setSortingEnabled(False)
        self.table_logs.setRowCount(len(self._data))
        self.table_logs.setColumnCount(len(self._columns))
        self.table_logs.setHorizontalHeaderLabels(self._headers)

        for row, data in enumerate(self._data):
            for col, col_key in enumerate(self._columns):
                item = QTableWidgetItem(data.get(col_key, ''))
                self.table_logs.setItem(row, col, item)

        for c in [0, 2, 3]:
            self.table_logs.resizeColumnToContents(c)

        self.table_logs.resizeRowsToContents()
        self.table_logs.setSortingEnabled(True)
        self.table_logs.scrollToBottom()
        self.table_logs.scrollToTop()
        self.table_logs.sortByColumn(1, Qt.AscendingOrder)

        # Make sure there is always a selected row
        self.table_logs.setCurrentCell(0, 0)

    def copy_item(self):
        """Copy selected item to clipboard in markdown format."""
        app = QApplication.instance()
        items = self.table_logs.selectedIndexes()
        if items:
            rows = set(sorted(i.row() for i in items))
            if self._data:
                all_data = [self._data[row] for row in rows]
                dump = json.dumps(all_data, sort_keys=True, indent=4)
                app.clipboard().setText('```json\n' + dump + '\n```')


# --- Local testing
# -----------------------------------------------------------------------------
def local_test():  # pragma: no cover
    """Run local test."""
    from anaconda_navigator.utils.qthelpers import qapplication
    app = qapplication()

    widget = LogViewerDialog()
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':  # pragma: no cover
    local_test()
