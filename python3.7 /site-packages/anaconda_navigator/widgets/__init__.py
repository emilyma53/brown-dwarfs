# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Wigets module."""

# yapf: disable

# Third party imports
from qtpy import QtSvg
from qtpy.QtCore import QSize, Qt, QUrl, Signal
from qtpy.QtGui import QDesktopServices
from qtpy.QtWidgets import (QCheckBox, QComboBox, QFrame, QLabel, QLineEdit,
                            QMenu, QPushButton, QSizePolicy, QStackedWidget,
                            QToolButton, QWidget)

# Local imports
from anaconda_navigator.utils.qthelpers import (add_actions, create_action,
                                                update_pointer)


# yapf: enable


# --- Base widgets
# -----------------------------------------------------------------------------
class WidgetBase(QWidget):
    """Widget base implementation."""

    sig_hovered = Signal(bool)
    sig_focused = Signal(bool)

    def _fix_style(self):
        # Mac related issues
        self.setAttribute(Qt.WA_LayoutUsesWidgetRect, True)
        self.setFocusPolicy(Qt.StrongFocus)

    def _fix_layout(self, layout):
        if layout:
            layout.setSpacing(0)
            layout.setContentsMargins(0, 0, 0, 0)

            items = (layout.itemAt(i).widget() for i in range(layout.count()))
            for w in items:
                if w:
                    new_layout = w.layout()
                    self._fix_layout(new_layout)

    def focusInEvent(self, event):
        """Override Qt method."""
        QWidget.focusInEvent(self, event)
        self.setProperty('focused', True)

    def focusOutEvent(self, event):
        """Override Qt method."""
        QWidget.focusOutEvent(self, event)
        self.setProperty('focused', False)

    def enterEvent(self, event):
        """Override Qt method."""
        QWidget.enterEvent(self, event)
        self.setProperty('hovered', True)

    def leaveEvent(self, event):
        """Override Qt method."""
        QWidget.leaveEvent(self, event)
        self.setProperty('hovered', False)

    def setDisabled(self, value):
        """Override Qt method."""
        QWidget.setDisabled(self, value)
        self.setProperty('disabled', value)
        self.setProperty('enabled', not value)

    def setEnabled(self, value):
        """Override Qt method."""
        QWidget.setEnabled(self, value)
        self.setProperty('enabled', value)
        self.setProperty('disabled', not value)

    def setProperty(self, name, value):
        """Override Qt method."""
        QWidget.setProperty(self, name, value)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def setLayout(self, layout):
        """Override Qt method."""
        self._fix_layout(layout)
        QWidget.setLayout(self, layout)


class ButtonBase(QPushButton, WidgetBase):
    """Base button used in CSS styling."""

    sig_entered = Signal()
    sig_left = Signal()

    def __init__(self, *args, **kwargs):
        """Base button used in CSS styling."""
        super(ButtonBase, self).__init__(*args, **kwargs)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setAttribute(Qt.WA_LayoutUsesWidgetRect, True)
        self.setFocusPolicy(Qt.StrongFocus)

    def focusInEvent(self, event):
        """Override Qt method."""
        super(ButtonBase, self).focusInEvent(event)
        self.sig_entered.emit()

    def focusOutEvent(self, event):
        """Override Qt method."""
        super(ButtonBase, self).focusOutEvent(event)
        self.sig_left.emit()

    def enterEvent(self, event):
        """Override Qt method."""
        super(ButtonBase, self).enterEvent(event)
        self.sig_entered.emit()

    def leaveEvent(self, event):
        """Override Qt method."""
        super(ButtonBase, self).leaveEvent(event)
        self.sig_left.emit()

    def mousePressEvent(self, event):
        """Override Qt method."""
        super(ButtonBase, self).mousePressEvent(event)
        self.setProperty('pressed', True)

    def mouseReleaseEvent(self, event):
        """Override Qt method."""
        super(ButtonBase, self).mouseReleaseEvent(event)
        self.setProperty('pressed', False)


class ButtonToolBase(QToolButton, WidgetBase):
    """Base button used in CSS styling."""

    def __init__(self, parent=None, text=''):
        """Base button used in CSS styling."""
        super(ButtonToolBase, self).__init__(parent=parent)
        self.setCheckable(False)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setText(text)
        self.setFocusPolicy(Qt.StrongFocus)  # Needed on OSX
        self.setAttribute(Qt.WA_LayoutUsesWidgetRect, True)  # Needed on OSX
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


class CheckBoxBase(QCheckBox, WidgetBase):
    """Checkbox used in CSS styling."""

    def __init__(self, *args, **kwargs):
        """Checkbox used in CSS styling."""
        super(CheckBoxBase, self).__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)  # Needed on OSX
        self.setAttribute(Qt.WA_LayoutUsesWidgetRect, True)  # Needed on OSX


class ComboBoxBase(QComboBox):
    """Combobox used in CSS styling."""

    def __init__(self, *args, **kwargs):
        """Combobox used in CSS styling."""
        super(ComboBoxBase, self).__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)  # Needed on OSX
        self.setAttribute(Qt.WA_LayoutUsesWidgetRect, True)  # Needed on OSX

    def showPopup(self):
        """Override Qt method."""
        index = self.currentIndex()
        menu = QMenu(self)

        # See: https://github.com/ContinuumIO/navigator/issues/1565
        try:
            menu.setToolTipsVisible(True)
        except AttributeError:
            pass

        actions = []

        for i in range(self.count()):
            tip = self.itemData(i, Qt.ToolTipRole)
            text = self.itemText(i)
            action = create_action(
                self,
                text,
                toggled=lambda v=None, i=i: self.setCurrentIndex(i),
                tip=tip
            )

            actions.append(action)

            if i == index:
                action.setChecked(True)

        add_actions(menu, actions)
        menu.setFixedWidth(self.width())
        bottom_left = self.contentsRect().bottomLeft()
        menu.popup(self.mapToGlobal(bottom_left))


class FrameBase(QFrame, WidgetBase):
    """Button used in CSS styling."""

    def __init__(self, *args, **kwargs):
        """Button used in CSS styling."""
        super(FrameBase, self).__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.NoFocus)  # Needed on OSX
        self.setAttribute(Qt.WA_LayoutUsesWidgetRect, True)  # Needed on OSX

    def setLayout(self, layout):
        """Override Qt method."""
        self._fix_layout(layout)
        super(FrameBase, self).setLayout(layout)


class LabelBase(QLabel, WidgetBase):
    """Label used in CSS styling."""

    def __init__(self, *args, **kwargs):
        """Label used in CSS styling."""
        super(LabelBase, self).__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.NoFocus)  # Needed on OSX
        self.setAttribute(Qt.WA_LayoutUsesWidgetRect, True)  # Needed on OSX


class StackBody(QStackedWidget, WidgetBase):
    """Stacked widget used in CSS styling of main custom bar stack."""

    def __init__(self, *args, **kwargs):
        """Stacked widget used in CSS styling of main custom bar stack."""
        super(StackBody, self).__init__(*args, **kwargs)
        self.setContentsMargins(0, 0, 0, 0)
        self.setFrameStyle(QFrame.NoFrame)
        self.setFocusPolicy(Qt.StrongFocus)  # Needed on OSX
        self.setAttribute(Qt.WA_LayoutUsesWidgetRect, True)  # Needed on OSX

    def setLayout(self, layout):
        """Override Qt method."""
        self._fix_layout(layout)
        super(StackBody, self).setLayout(layout)


class LineEditBase(QLineEdit):
    """Line edit used in CSS styling."""

    def __init__(self, *args, **kwargs):
        """Line edit used in CSS styling."""
        super(LineEditBase, self).__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)  # Needed on OSX
        self.setAttribute(Qt.WA_LayoutUsesWidgetRect, True)  # Needed on OSX

    def mousePressEvent(self, event):
        """Override Qt method."""
        super(LineEditBase, self).mousePressEvent(event)
        self.setProperty('pressed', True)

    def mouseReleaseEvent(self, event):
        """Override Qt method."""
        super(LineEditBase, self).mouseReleaseEvent(event)
        self.setProperty('pressed', False)


# --- Buttons
# -----------------------------------------------------------------------------
class ButtonToolNormal(ButtonToolBase):
    """Button used in CSS styling."""


class ButtonNormal(ButtonBase):
    """Button used in CSS styling."""


class ButtonPrimary(ButtonBase):
    """Button used in CSS styling."""


class ButtonDanger(ButtonBase):
    """Button used in CSS styling."""


class ButtonLink(QPushButton, WidgetBase):
    """
    Button use to represent a clickable (and keyboard focusable) web link.

    It is styled to be used as a label.
    """

    sig_hovered = Signal(bool)

    def __init__(self, *args, **kwargs):
        """
        Button use to represent a clickable (and keyboard focusable) web link.

        It is styled to be used as a label.
        """
        super(ButtonLink, self).__init__(*args, **kwargs)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setFocusPolicy(Qt.StrongFocus)  # Needed on OSX
        self.setAttribute(Qt.WA_LayoutUsesWidgetRect, True)  # Needed on OSX

    def enterEvent(self, event):
        """Override Qt method."""
        super(ButtonLink, self).enterEvent(event)
        update_pointer(Qt.PointingHandCursor)
        self.sig_hovered.emit(True)

    def leaveEvent(self, event):
        """Override Qt method."""
        super(ButtonLink, self).leaveEvent(event)
        update_pointer()
        self.sig_hovered.emit(False)


class ButtonLabel(QPushButton):
    """
    A button that is used next to ButtonLink to avoid missalignments.

    It looks and acts like a label.
    """

    def __init__(self, *args, **kwargs):
        """A button that is used next to ButtonLink to avoid missalignments."""
        super(ButtonLabel, self).__init__(*args, **kwargs)
        self.setDisabled(True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_LayoutUsesWidgetRect, True)  # Needed on mac


# --- Frames
# -----------------------------------------------------------------------------
class FrameTabBar(FrameBase):
    """Frame used in CSS styling."""


class FrameTabBody(FrameBase):
    """Frame used in CSS styling."""


class FrameTabHeader(FrameBase):
    """Frame used in CSS styling."""


class FrameTabContent(FrameBase):
    """Frame used in CSS styling."""


class FrameTabFooter(FrameBase):
    """Frame used in CSS styling."""

    pass


# --- Labels
# -----------------------------------------------------------------------------
class LabelLinks(LabelBase):
    """Label link used as url link."""

    LINKS_STYLE = """<style>
    a {
        color:green;
        text-decoration: underline;
    }
    </style>
    """

    def __init__(self, *args, **kwargs):
        """Label link used as url link."""
        super(LabelLinks, self).__init__(*args, **kwargs)
        self.setOpenExternalLinks(False)
        self.linkActivated.connect(self._link_activated)
        self._original_text = self.text()
        self._add_style()

    def _add_style(self):
        text = self._original_text
        if self.LINKS_STYLE not in text:
            self.setText(self.LINKS_STYLE + text)

    @staticmethod
    def _link_activated(url):
        QDesktopServices.openUrl(QUrl(url))
        from anaconda_navigator.utils.analytics import GATracker
        tracker = GATracker()
        tracker.track_event('content', 'link', url)

    def setText(self, text):
        """Override Qt method."""
        self._original_text = text
        super(LabelLinks, self).setText(text)
        self._add_style()


# --- Spacers
# -----------------------------------------------------------------------------
class SpacerHorizontal(LabelBase):
    """Label used in CSS styling."""


class SpacerVertical(LabelBase):
    """Label used in CSS styling."""

    pass


# --- Other Buttons
# -----------------------------------------------------------------------------
class ButtonPrimaryAction(QPushButton):
    """Button used in CSS styling."""


class ButtonCancel(QPushButton):
    """Button used in CSS styling."""


class ButtonSecondaryTextual(QPushButton):
    """Button used in CSS styling."""


class ButtonSecondaryIcon(QPushButton):
    """Button used in CSS styling."""


class ButtonEnvironmentCancel(QPushButton):
    """Button used in CSS styling."""


class ButtonEnvironmentPrimary(QPushButton):
    """Button used in CSS styling."""

    pass


# --- Buttons that are used as labels.
class ButtonEnvironmentOptions(ButtonBase):
    """Button used in CSS styling."""


class FrameEnvironments(QFrame):
    """Frame used in CSS styling."""


class FrameEnvironmentsList(QFrame):
    """Frame used in CSS styling."""


class FrameEnvironmentsListButtons(QFrame):
    """Frame used in CSS styling."""


class FrameEnvironmentsPackages(QFrame):
    """Frame used in CSS styling."""

    pass


class QSvgWidget(QtSvg.QSvgWidget):
    """SvgWidget that knows about its size ratio."""

    def __init__(self, *args, **kwargs):
        """SvgWidget that knows about its size ratio."""
        super(QSvgWidget, self).__init__(*args, **kwargs)

        # Variables
        self._path = None
        if args:
            self._path = args[0]
        self._default_size = self._get_default_size()

        # Widget setup
        self.setAttribute(Qt.WA_LayoutUsesWidgetRect, True)

    def _get_default_size(self):
        """Get dfault size of SVG image."""
        size = QSize()
        if self._path:
            item = QtSvg.QGraphicsSvgItem(self._path)
            size = item.renderer().defaultSize()
        return size

    def size_for_width(self, width):
        """Return the size for a given width, preserving the ratio."""
        size = self.default_size()
        ratio_w_h = size.width() / size.height()
        return QSize(width, width / ratio_w_h)

    def size_for_height(self, height):
        """Return the size for a given height, preserving the ratio."""
        size = self.default_size()
        ratio_w_h = size.width() / size.height()
        return QSize(height * ratio_w_h, height)

    def default_size(self):
        """Return the default size of the SVG image."""
        return self._default_size
