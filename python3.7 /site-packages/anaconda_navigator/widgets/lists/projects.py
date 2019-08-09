# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Widgets to list environemnts available to edit in the Environments tab."""

from __future__ import absolute_import, division, print_function

# Standard library imports
import sys

# Third party imports
from qtpy.QtCore import QSize, Qt, Signal
from qtpy.QtGui import QMovie
from qtpy.QtWidgets import QHBoxLayout, QLabel, QPushButton

# Local imports
from anaconda_navigator.static.images import SPINNER_GREEN_16_PATH
from anaconda_navigator.utils.qthelpers import qapplication
from anaconda_navigator.utils.styles import SASS_VARIABLES, load_style_sheet
from anaconda_navigator.widgets import ButtonEnvironmentOptions, FrameBase
from anaconda_navigator.widgets.lists import ListWidgetBase, ListWidgetItemBase


# --- Widgets used in styling
# -----------------------------------------------------------------------------
class WidgetEnvironment(FrameBase):
    """Main list item widget used in CSS styling."""

    sig_entered = Signal()
    sig_left = Signal()
    clicked = Signal()

    def __init__(self, *args, **kwargs):
        """Main list item widget used in CSS styling."""
        super(WidgetEnvironment, self).__init__(*args, **kwargs)
        self._hover = False

    def keyPressEvent(self, event):
        """Override Qt method."""
        key = event.key()
        if key in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space]:
            self.clicked.emit()
        super(WidgetEnvironment, self).keyPressEvent(event)

    def enterEvent(self, event):
        """Override Qt method."""
        super(WidgetEnvironment, self).enterEvent(event)
        self._hover = True
        self.sig_entered.emit()

    def leaveEvent(self, event):
        """Override Qt method."""
        super(WidgetEnvironment, self).enterEvent(event)
        self._hover = False
        self.sig_left.emit()

    def mouseReleaseEvent(self, event):
        """Override Qt method."""
        super(WidgetEnvironment, self).enterEvent(event)
        if self._hover:
            self.clicked.emit()


class ButtonEnvironmentName(QPushButton):
    """Button used in CSS styling."""

    sig_entered = Signal()
    sig_left = Signal()

    def focusInEvent(self, event):
        """Override Qt method."""
        super(ButtonEnvironmentName, self).focusInEvent(event)
        self.sig_entered.emit()

    def focusOutEvent(self, event):
        """Override Qt method."""
        super(ButtonEnvironmentName, self).focusOutEvent(event)
        self.sig_left.emit()

    def enterEvent(self, event):
        """Override Qt method."""
        super(ButtonEnvironmentName, self).enterEvent(event)
        self.sig_entered.emit()

    def leaveEvent(self, event):
        """Override Qt method."""
        super(ButtonEnvironmentName, self).enterEvent(event)
        self.sig_left.emit()

    def setProperty(self, name, value):
        """Override Qt method."""
        QPushButton.setProperty(self, name, value)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def set_selected(self, value):
        """Set selected status."""
        self._selected = value
        self.setProperty('pressed', value)

    def set_hovered(self, value):
        """Set hovered status."""
        self.setProperty('hovered', value)


class LabelEnvironmentIcon(QLabel):
    """Label used in CSS styling."""

    pass


# --- Main widgets
# -----------------------------------------------------------------------------
class ListWidgetEnv(ListWidgetBase):
    """Custom list widget environments."""

    def ordered_widgets(self):
        """Return a list of the ordered widgets."""
        ordered_widgets = []
        for item in self.items():
            ordered_widgets += item.ordered_widgets()
        return ordered_widgets

    def setup_item(self, item):
        """Add additional logic after adding an item."""
        index = self._items.index(item)

        item.widget.clicked.connect(
            lambda v=None, i=index: self.setCurrentRow(i, loading=True)
        )
        item.widget.clicked.connect(
            lambda v=None, it=item: self.sig_item_selected.emit(it)
        )
        item.widget.sig_entered.connect(lambda v=None: item.set_hovered(True))
        item.widget.sig_left.connect(lambda v=None: item.set_hovered(False))
        item.button_name.clicked.connect(
            lambda v=None, it=item: self.sig_item_selected.emit(it)
        )
        item.button_name.clicked.connect(
            lambda v=None, i=index: self.setCurrentRow(i, loading=True)
        )
        item.button_name.sig_entered.connect(
            lambda v=None: item.set_hovered(True)
        )
        item.button_name.sig_left.connect(
            lambda v=None: item.set_hovered(False)
        )

        fm = item.button_name.fontMetrics()
        elided_name = fm.elidedText(item.name, Qt.ElideRight, 150)
        item.button_name.setText(elided_name)

    def text(self):
        """
        Override Qt Method.

        Return full name, not elided text.
        """
        item = self.currentItem()
        text = ''
        if item:
            text = item.name
        return text


class ListItemEnv(ListWidgetItemBase):
    """Widget to build an item for the environments list."""

    def __init__(self, name=None, prefix=None):
        """Widget to build an item for the environments list."""
        super(ListItemEnv, self).__init__()

        self._selected = False
        self._name = name
        self._prefix = prefix

        # Widgets
        self.button_options = ButtonEnvironmentOptions()
        self.button_name = ButtonEnvironmentName(name)
        self.label_icon = LabelEnvironmentIcon()
        self.movie = QMovie(SPINNER_GREEN_16_PATH)
        self.widget = WidgetEnvironment()
        self.widget.button_name = self.button_name
        self.widget.button_options = self.button_options

        # Widget setup
        self.button_name.setDefault(True)
        self.label_icon.setMovie(self.movie)
        self.widget.setFocusPolicy(Qt.NoFocus)
        self.button_name.setFocusPolicy(Qt.StrongFocus)
        self.button_options.setFocusPolicy(Qt.StrongFocus)

        # Layouts
        layout = QHBoxLayout()
        layout.addWidget(self.label_icon)
        layout.addWidget(self.button_name)
        layout.addWidget(self.button_options)
        layout.addStretch()

        self.widget.setLayout(layout)
        self.widget.setStyleSheet(load_style_sheet())
        self.setSizeHint(self.widget.sizeHint())

    def ordered_widgets(self):
        """Return a list of the ordered widgets."""
        return [self.button_name, self.button_options]

    def text(self):
        """Resturn the name of item."""
        return self._name

    @property
    def name(self):
        return self._name

    def prefix(self):
        """Return environment prefix."""
        return self._prefix

    def set_hovered(self, value):
        """Set widget as hovered."""
        self.widget.setProperty('hovered', value)
        self.button_name.set_hovered(value)

    def set_loading(self, value):
        """Set loading status of widget."""
        # self.button_options.setDisabled(value)
        #        if value:
        #            self.label_icon.setMovie(self.movie)
        #            self.movie.start()
        #        else:
        #            self.label_icon.setMovie(QMovie())
        #            self.button_options.setFocus()
        self.label_icon.setMovie(QMovie())
        self.button_options.setFocus()

    def set_selected(self, value):
        """Set widget as selected."""
        self._selected = value
        try:
            self.widget.setProperty('pressed', value)
            self.button_name.set_selected(value)
        except RuntimeError:
            pass

        self.button_name.setDisabled(value)

        if value:
            self.label_icon.setMovie(None)
            self.button_options.setVisible(True)
        else:
            self.label_icon.setMovie(None)
            self.button_options.setVisible(False)
        self.button_options.setVisible(False)

    @staticmethod
    def widget_size():
        """Return the size defined in the SASS file."""
        return QSize(
            SASS_VARIABLES.WIDGET_ENVIRONMENT_TOTAL_WIDTH,
            SASS_VARIABLES.WIDGET_ENVIRONMENT_TOTAL_HEIGHT
        )


# --- Local testing
# -----------------------------------------------------------------------------
def print_selected(item):
    """Print selected item name."""
    print('Item selected: ', item.text())


def local_test():  # pragma: no cover
    """Run local test."""
    app = qapplication()
    widget = ListWidgetEnv()
    widget.sig_item_selected.connect(print_selected)
    widget.addItem(ListItemEnv('root'))

    for i in range(5):
        item = ListItemEnv('env ' + str(i))
        widget.addItem(item)

    widget.update_style_sheet()
    widget.show()
    sys.exit(app.exec_())


if __name__ == "__main__":  # pragma: no cover
    local_test()
