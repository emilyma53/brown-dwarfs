# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Custom tab widget with custom tabbar."""

# yapf: disable

# Standard library imports
import sys

# Third party imports
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout,
                            QWidget)

# Local imports
from anaconda_navigator.utils.styles import load_style_sheet
from anaconda_navigator.widgets import (ButtonLink, ButtonToolBase, FrameBase,
                                        FrameTabBar, FrameTabBody, LabelBase,
                                        StackBody)


# yapf: enable


class LabelTabHeader(LabelBase):
    """Label used in CSS styling."""


class FrameTabBarBottom(FrameBase):
    """Frame used in CSS styling."""


class FrameTabBarLink(FrameBase):
    """Frame used in CSS styling."""


class FrameTabBarSocial(FrameBase):
    """Frame used in CSS styling."""


class ButtonTab(ButtonToolBase):
    """Button used in custom tab bar for CSS styling."""

    def __init__(self, *args, **kwargs):
        """Button used in custom tab bar for CSS styling."""
        super(ButtonTab, self).__init__(*args, **kwargs)
        self.setCheckable(True)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def keyPressEvent(self, event):
        """Override Qt method."""
        key = event.key()
        if key in [Qt.Key_Enter, Qt.Key_Return]:
            self.animateClick()
        super(ButtonTab, self).keyPressEvent(event)


class TabBar(QWidget):
    """Custom QTabBar that includes centered icons and text bellow the icon."""

    sig_index_changed = Signal(int)
    sig_url_clicked = Signal(object)

    def __init__(self, *args, **kwargs):
        """Custom QTabBar."""
        super(TabBar, self).__init__(*args, **kwargs)
        self.buttons = []
        self.links = []
        self.links_social = []
        self.frame_bottom = FrameTabBarBottom()
        self.frame_social = FrameTabBarSocial()
        self.frame_link = FrameTabBarLink()
        self.current_index = None

        # Layouts
        self.layout_top = QVBoxLayout()
        self.layout_link = QVBoxLayout()
        self.layout_social = QHBoxLayout()
        self._label_links_header = LabelTabHeader('')

        layout = QVBoxLayout()
        layout.addLayout(self.layout_top)
        layout.addStretch()

        self.frame_link.setLayout(self.layout_link)
        self.frame_social.setLayout(self.layout_social)

        layout_bottom = QVBoxLayout()
        layout_bottom.addWidget(self.frame_link)
        layout_bottom.addWidget(self.frame_social)
        self.frame_bottom.setLayout(layout_bottom)

        layout.addWidget(self.frame_bottom)
        #        self.layout_bottom.addWidget(self._label_links_header, 0,
        #                                     Qt.AlignLeft)
        self.setLayout(layout)

    def set_links_header(self, text):
        """Add links header to the bottom of the custom tab bar."""
        self._label_links_header.setText(text)

    def add_social(self, text, url=None):
        """Add social link on bottom of side bar."""
        button = ButtonLink()
        button.setText(' ')
        button.setObjectName(text.lower())
        button.setFocusPolicy(Qt.StrongFocus)
        button.clicked.connect(
            lambda v=None, url=url: self.sig_url_clicked.emit(url)
        )
        self.layout_social.addWidget(button, 0, Qt.AlignCenter)
        self.links_social.append(button)

    def add_link(self, text, url=None):
        """Add link on bottom of side bar."""
        button = ButtonLink()
        button.setText(text)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        button.setFocusPolicy(Qt.StrongFocus)
        button.clicked.connect(
            lambda v=None, url=url: self.sig_url_clicked.emit(url)
        )
        self.layout_link.addWidget(button)
        self.links.append(button)

    def add_tab(self, text, icon=None):
        """Create the widget that replaces the normal tab content."""
        button = ButtonTab()
        button.setObjectName(text.lower())
        if text == 'Projects':
            text = 'Projects (beta)'
        button.setText(text)
        button.setFocusPolicy(Qt.StrongFocus)

        if icon:
            button.setIcon(icon)

        self.layout_top.addWidget(button)
        self.buttons.append(button)
        index = self.buttons.index(button)
        button.clicked.connect(
            lambda b=button, i=index: self.refresh(button, index)
        )

    def refresh(self, button=None, index=None):
        """Refresh pressed status of buttons."""
        widths = []
        for b in self.buttons:
            b.setChecked(False)
            b.setProperty('checked', False)
            widths.append(b.width())

        max_width = max(widths)
        for b in self.buttons:
            b.setMinimumWidth(max_width)

        if button:
            button.setChecked(True)
            button.setProperty('checked', True)

        if index is not None:
            self.sig_index_changed.emit(index)
            self.current_index = index


class TabWidget(QWidget):
    """Curstom Tab Widget that includes a more customizable `tabbar`."""

    sig_current_changed = Signal(int)
    sig_url_clicked = Signal(object)

    def __init__(self, *args, **kwargs):
        """Custom Tab Widget that includes a more customizable `tabbar`."""
        super(TabWidget, self).__init__(*args, **kwargs)
        self.frame_sidebar = FrameTabBar()
        self.frame_tab_content = FrameTabBody()
        self.stack = StackBody()
        self.tabbar = TabBar()

        layout_sidebar = QVBoxLayout()
        layout_sidebar.addWidget(self.tabbar)
        self.frame_sidebar.setLayout(layout_sidebar)

        layout_content = QHBoxLayout()
        layout_content.addWidget(self.stack)
        self.frame_tab_content.setLayout(layout_content)

        layout = QHBoxLayout()
        layout.addWidget(self.frame_sidebar)
        layout.addWidget(self.frame_tab_content)

        self.setLayout(layout)
        self.tabbar.sig_index_changed.connect(self.setCurrentIndex)

        self.tabbar.sig_url_clicked.connect(self.sig_url_clicked)

    def count(self):
        """Override Qt method."""
        return self.stack.count()

    def widget(self, index):
        """Override Qt method."""
        return self.stack.widget(index)

    def currentWidget(self):
        """Override Qt method."""
        return self.stack.currentWidget()

    def currentIndex(self):
        """Override Qt method."""
        return self.tabbar.current_index

    def setCurrentIndex(self, index):
        """Override Qt method."""
        if self.currentIndex() != index:
            self.tabbar.current_index = index
            self.tabbar.buttons[index].setChecked(True)
            self.tabbar.buttons[index].setFocus()
            self.stack.setCurrentIndex(index)
            self.sig_current_changed.emit(index)

    def currentText(self):
        """Override Qt method."""
        index = self.currentIndex()
        text = ''
        if index:
            button = self.tabbar.buttons[self.currentIndex()]
            if button:
                text = button.text()
        return text

    def addTab(self, widget, icon=None, text=''):
        """Override Qt method."""
        if widget:
            self.tabbar.add_tab(text, icon)
            self.stack.addWidget(widget)
            self.setCurrentIndex(0)
        else:
            raise Exception('tab widget cant be None')

    def add_link(self, text, url=None):
        """Add links to the bottom area of the custom tab bar."""
        self.tabbar.add_link(text, url)

    def add_social(self, text, url=None):
        """Add social link on bottom of side bar."""
        self.tabbar.add_social(text, url)

    def set_links_header(self, text):
        """Add links header to the bottom of the custom tab bar."""
        self.tabbar.set_links_header(text)

    def refresh(self):
        """Refresh size of buttons."""
        self.tabbar.refresh()


# --- Local testing
# -----------------------------------------------------------------------------
def local_test():  # pragma: no cover
    """Run local tests."""
    from anaconda_navigator.utils.qthelpers import qapplication

    app = qapplication(test_time=3)
    widget = TabWidget()
    widget.addTab(QLabel('HELLO 1'), text='Home', icon=QIcon())
    widget.addTab(QLabel('HELLO 2'), text='Add', icon=QIcon())
    widget.add_link('link 1')
    widget.setStyleSheet(load_style_sheet())
    widget.showMaximized()
    widget.refresh()
    sys.exit(app.exec_())


if __name__ == '__main__':  # pragma: no cover
    local_test()
