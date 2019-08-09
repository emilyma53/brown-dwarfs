# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Lists module."""

# yapf: disable

# Third party imports
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (QAbstractItemView, QFrame, QListWidget,
                            QListWidgetItem)

# Local imports
from anaconda_navigator.utils.styles import load_style_sheet


# yapf: enable


class ListWidgetBase(QListWidget):
    """Base list widget."""

    sig_item_selected = Signal(object)

    def __init__(self, *args, **kwargs):
        """Custom list widget environments."""
        super(ListWidgetBase, self).__init__(*args, **kwargs)
        self._items = []
        self._current_item = None
        self.style_sheet = None

        # Widget setup
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.setFrameStyle(QFrame.Plain)
        self.setFocusPolicy(Qt.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMovement(QListWidget.Static)
        self.setResizeMode(QListWidget.Adjust)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setViewMode(QListWidget.ListMode)

    # --- Qt overrided methods
    # -------------------------------------------------------------------------
    def addItem(self, item):
        """Add an item to the list."""
        QListWidget.addItem(self, item)
        self._items.append(item)
        self.setItemWidget(item, item.widget)
        item.setSizeHint(item.widget_size())

        self.setup_item(item)

        if self._current_item is None:
            self._current_item = item
            self.setCurrentRow(0)
        else:
            item.set_selected(False)

        if self.style_sheet:
            item.widget.setStyleSheet(self.style_sheet)

    def insertItem(self, row, item):
        """Override Qt method."""
        QListWidget.insertItem(self, row, item)
        self._items = self._items[:row] + [item] + self._items[row:]
        self.setItemWidget(item, item.widget)
        item.setSizeHint(item.widget_size())
        self.setup_item(item)

        if self._current_item is None:
            self._current_item = item
            self.setCurrentRow(0)
        else:
            item.set_selected(False)

        if self.style_sheet:
            item.widget.setStyleSheet(self.style_sheet)

    def clear(self):
        """Clear all list items and references."""
        super(ListWidgetBase, self).clear()
        self._items = []

    def count(self):
        """Override Qt Method."""
        return len(self._items)

    def setCurrentRow(self, row, loading=False):
        """Override Qt method."""
        for i, item in enumerate(self._items):
            if i == row:
                item.set_selected(True)
                item.set_loading(loading)
                self._current_item = item
            else:
                item.set_selected(False)
                item.set_loading(False)

    def currentItem(self):
        """Override Qt method."""
        return self._current_item

    def currentIndex(self):
        """Override Qt method."""
        if self._current_item in self._items:
            return self._items.index(self._current_item)
        else:
            return None

    def item(self, index):
        """Override Qt method."""
        return self._items[index]

    def items(self):
        """Override Qt method."""
        return self._items

    def scroll_to_item(self, item):
        """Scroll to item with focus."""
        try:
            self.scrollToItem(item)
        except RuntimeError:
            pass

    # --- Custom methods
    # -------------------------------------------------------------------------
    def setup_item(self, item):
        """Add additional logic after adding an item."""
        print(self, 'Must oveload this method')
        raise NotImplementedError

    def update_style_sheet(self, style_sheet=None):
        """Update custom CSS style sheet."""
        if self.style_sheet:
            self.style_sheet = style_sheet
        else:
            self.style_sheet = load_style_sheet()

        self.setStyleSheet(self.style_sheet)

        for item in self._items:
            try:
                item_widget = self.itemWidget(item)
                item_widget.setStyleSheet(self.style_sheet)
                item.update_style_sheet(self.style_sheet)
                item.setSizeHint(item.widget_size())
            except Exception as e:
                print(e)
                # This error is just in case the C++ object has been deleted
                # and it is not crucial to log.
                pass

        self.update()
        self.repaint()


class ListWidgetItemBase(QListWidgetItem):
    """Base list widget item."""

    def set_loading(self, value):
        """Set loading status of widgets."""
        pass

    def set_selected(self, value):
        """Set selected status of widgets."""
        pass

    def update_style_sheet(self, style_sheet):
        """Set style sheet."""
        pass
