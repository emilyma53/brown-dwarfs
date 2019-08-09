# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""License Manager Dialog."""

# yapf: disable

# Third party imports
from qtpy.compat import getopenfilename
from qtpy.QtCore import (QAbstractTableModel, QModelIndex,
                         QSortFilterProxyModel, Qt, Signal)
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (QAbstractItemView, QHBoxLayout, QStyle,
                            QStyledItemDelegate, QTableView, QVBoxLayout)

# Local imports
from anaconda_navigator.api.anaconda_api import AnacondaAPI
from anaconda_navigator.config import LICENSE_PATH, get_home_dir
from anaconda_navigator.utils.qthelpers import qapplication
from anaconda_navigator.widgets import (ButtonLink, ButtonNormal,
                                        ButtonPrimary, LabelBase,
                                        SpacerHorizontal, SpacerVertical)
from anaconda_navigator.widgets.dialogs import (DialogBase,
                                                MessageBoxInformation,
                                                MessageBoxRemove)


# yapf: enable

# Extra data added to the license dicts to track the file it comes from
# Defined as a constant as it is used in several places so this avoidd hard
# coding a string
COL_MAP = {
    0: '__type__',
    1: 'product',
    2: 'end_date',
    3: '__status__',
    4: 'sig',
    5: LICENSE_PATH,
}

HIDDEN_COLUMNS = [LICENSE_PATH, 'sig']


class LicenseModel(QAbstractTableModel):
    """Table model for the license view."""

    def __init__(self, parent=None, licenses=None):
        """Table model for the license view."""
        super(LicenseModel, self).__init__(parent=parent)
        self._parent = parent
        self._rows = licenses if licenses else []

    @staticmethod
    def flags(index):
        """Override Qt method."""
        if index.isValid():
            return Qt.ItemFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

    def data(self, index, role=Qt.DisplayRole):
        """Override Qt method."""
        if index is None:
            return None
        else:
            if not index.isValid() or not 0 <= index.row() < len(self._rows):
                return None

        row = index.row()
        column = index.column()
        license_data = self._rows[row]

        if role == Qt.DisplayRole:
            data_key = COL_MAP.get(column)
            if data_key:
                return license_data.get(data_key)
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        return

    @staticmethod
    def headerData(section, orientation, role=Qt.DisplayRole):
        """Override Qt method."""
        title = COL_MAP.get(section)
        title = title.replace('__', '')
        title = title.replace('_', ' ').capitalize()

        if orientation == Qt.Horizontal:
            if role == Qt.TextAlignmentRole:
                return int(Qt.AlignHCenter | Qt.AlignVCenter)
            elif role == Qt.DisplayRole:
                return title

    def rowCount(self, index=QModelIndex()):
        """Override Qt method."""
        return len(self._rows)

    @staticmethod
    def columnCount(index=QModelIndex()):
        """Override Qt method."""
        return len(COL_MAP)

    # --- Helpers
    # -------------------------------------------------------------------------
    def row(self, rownum):
        """Return the row data."""
        return self._rows[rownum] if rownum < len(self._rows) else None

    def load_licenses(self, licenses=None):
        """(Re)Load license data."""
        self._rows = licenses if licenses else []


class BackgroundDelegate(QStyledItemDelegate):
    """
    Delegate for handling background color in table.

    QTableView CSS styling rules are too limited so in order to get an even
    styling that matches the overall look, this delegate is needed.
    """

    def __init__(self, parent=None):
        """Delegate for handling background color in table."""
        super(BackgroundDelegate, self).__init__(parent=parent)
        self._parent = parent

    def paint(self, painter, option, index):
        """Override Qt method."""
        # To draw a border on selected cells
        if option.state & QStyle.State_Selected:
            if self._parent.hasFocus():
                color = QColor('#43B02A')  # TODO: Get this from the scss
            else:
                color = QColor('#cecece')  # TODO: Get this from the scss

            painter.save()
            painter.fillRect(option.rect, color)
            painter.restore()

            # Disable the state for the super() painter method
            option.state ^= QStyle.State_Selected

        super(BackgroundDelegate, self).paint(painter, option, index)


class LicenseTableView(QTableView):
    """License table manager view."""

    sig_dropped = Signal(object)
    sig_entered = Signal()
    sig_left = Signal()

    def __init__(self, parent=None):
        """License table manager view."""
        super(LicenseTableView, self).__init__(parent=parent)
        self.setMinimumWidth(500)
        self.setMinimumHeight(200)
        self.setAcceptDrops(True)
        self.setShowGrid(False)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().hide()
        self.horizontalHeader().setStretchLastSection(True)

    def focusInEvent(self, event):
        """Override Qt Method."""
        super(LicenseTableView, self).focusInEvent(event)
        self.sig_entered.emit()

    def focusOutEvent(self, event):
        """Override Qt Method."""
        super(LicenseTableView, self).focusInEvent(event)
        self.sig_left.emit()

    def dragEnterEvent(self, event):
        """Override Qt Method."""
        self.setProperty('dragin', True)
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Override Qt Method."""
        self.setProperty('dragin', False)

    @staticmethod
    def dragMoveEvent(event):
        """Override Qt Method."""
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Override Qt Method."""
        self.setProperty('dragin', False)
        mimedata = event.mimeData()
        if mimedata.hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            links = []
            for url in mimedata.urls():
                links.append(str(url.toLocalFile()))
            self.sig_dropped.emit(tuple(links))
        else:
            event.ignore()

    def setProperty(self, name, value):
        """Override Qt method."""
        QTableView.setProperty(self, name, value)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class LicenseManagerDialog(DialogBase):
    """License Manager main dialog."""

    CONTACT_LINK = 'https://support.continuum.io/'  # TODO: Centralize this?

    # Url, Sender
    sig_url_clicked = Signal(object, object)

    def __init__(self, parent=None):
        """License Manager main dialog."""
        super(LicenseManagerDialog, self).__init__(parent=parent)

        self.api = AnacondaAPI()

        # Widgets
        self.message_box = None  # For testing
        self.button_add = ButtonPrimary('Add license')
        self.button_ok = ButtonNormal('Close')
        self.button_remove = ButtonNormal('Remove license')
        self.button_contact = ButtonLink('Please contact us.')
        self.label_info = LabelBase(
            'Manage your Continuum Analytics '
            'license keys.'
        )
        self.label_contact = LabelBase('Got a problem with your license? ')
        self.proxy_model = QSortFilterProxyModel(parent=self)
        self.model = LicenseModel(parent=self)
        self.table = LicenseTableView(parent=self)
        self.delegate = BackgroundDelegate(self.table)

        # Widget setup
        self.proxy_model.setSourceModel(self.model)
        self.table.setItemDelegate(self.delegate)
        self.table.setModel(self.proxy_model)
        self.setWindowTitle('License Manager')

        # Layouts
        layout_buttons = QHBoxLayout()
        layout_buttons.addWidget(self.label_info)
        layout_buttons.addWidget(SpacerHorizontal())
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.button_add)
        layout_buttons.addWidget(SpacerHorizontal())
        layout_buttons.addWidget(self.button_remove)

        layout_buttons_bottom = QHBoxLayout()
        layout_buttons_bottom.addWidget(self.label_contact)
        layout_buttons_bottom.addWidget(self.button_contact)
        layout_buttons_bottom.addStretch()
        layout_buttons_bottom.addWidget(self.button_ok)

        layout = QVBoxLayout()
        layout.addLayout(layout_buttons)
        layout.addWidget(SpacerVertical())
        layout.addWidget(self.table)
        layout.addWidget(SpacerVertical())
        layout.addWidget(SpacerVertical())
        layout.addLayout(layout_buttons_bottom)
        self.setLayout(layout)

        # Signals
        self.button_add.clicked.connect(lambda: self.add_license())
        self.button_remove.clicked.connect(self.remove_license)
        self.button_ok.clicked.connect(self.accept)
        self.button_contact.clicked.connect(
            lambda v=None: self.sig_url_clicked.
            emit(self.CONTACT_LINK, 'License Manager')
        )
        self.table.sig_dropped.connect(self.handle_drop)

        # Setup
        self.button_add.setFocus()
        self.load_licenses()

    def handle_drop(self, links):
        """Handle a drag and drop event."""
        self.api.add_license(links)
        self.load_licenses()

    def _hide_columns(self):
        """Hide columns."""
        for key, val in COL_MAP.items():
            if val in HIDDEN_COLUMNS:
                self.table.setColumnHidden(key, True)

    def add_license(self, v=None, path=None):
        """Add license file."""
        if path is None:
            filename, selected_filter = getopenfilename(
                self,
                'Select license file',
                filters='License files (*.txt)',
                basedir=get_home_dir(),
            )

            if filename:
                paths = [filename]
            else:
                paths = []
        else:
            paths = [path]

        valid_licenses, invalid_licenses = self.api.add_license(paths)

        for path in invalid_licenses:
            text = ('File: <b>"{0}"</b>'
                    '<br>is not a valid license file.').format(path)
            self.message_box = MessageBoxInformation(
                text=text, title="Invalid license file"
            )
            self.message_box.exec_()

        if valid_licenses:
            self.load_licenses()

    def remove_license(self, row=None):
        """Remove license from file."""
        if row is None:
            index = self.table.currentIndex()
        else:
            index = self.proxy_model.index(row, 0)

        model_index = self.proxy_model.mapToSource(index)
        row_data = self.model.row(model_index.row())

        if row_data:
            text = (
                'Do you want to remove license for product:<br><br>'
                '<b>{product}</b> ({issued} - {end_date})'
            )
            text = text.format(
                product=row_data.get('product'),
                end_date=row_data.get('end_date'),
                issued=row_data.get('issued')
            )
            self.message_box = MessageBoxRemove(
                title='Remove license', text=text
            )
            if self.message_box.exec_():
                self.api.remove_license(row_data)
                self.load_licenses()

    def load_licenses(self):
        """Load license files."""
        res = self.api.load_licenses()
        self.model.load_licenses(res)
        self.proxy_model.setSourceModel(self.model)
        self.table.resizeColumnsToContents()
        self._hide_columns()
        self.update_status()

    def count(self):
        """Return the number of items in the table."""
        return self.table.model().rowCount()

    def update_status(self):
        """Update visible and enabled status for widgets based on actions."""
        self.button_remove.setEnabled(bool(self.count()))


def local_test():  # pragma: no cover
    """Run local test."""
    app = qapplication()
    w = LicenseManagerDialog()
    w.update_style_sheet()
    w.show()
    app.exec_()


if __name__ == '__main__':  # pragma: no cover
    local_test()
