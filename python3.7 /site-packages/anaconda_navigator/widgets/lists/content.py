# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Widgets to list videos available to launch on the learning tab."""

# yapf: disable

from __future__ import absolute_import, division

# Standard library imports
import os
import random
import sys

# Third party imports
from qtpy.QtCore import (QPoint, QRect, QSize, QSizeF, Qt, QTimeLine, QTimer,
                         QUrl, Signal)
from qtpy.QtGui import (QBrush, QColor, QDesktopServices, QFont, QPainter,
                        QPen, QTextDocument)
from qtpy.QtWidgets import QApplication, QHBoxLayout, QListWidget, QVBoxLayout

# Local imports
from anaconda_navigator.utils.analytics import GATracker
from anaconda_navigator.utils.styles import SASS_VARIABLES
from anaconda_navigator.widgets import ButtonBase, FrameBase, QLabel
from anaconda_navigator.widgets.dialogs import LabelBase
from anaconda_navigator.widgets.lists import ListWidgetBase, ListWidgetItemBase


# yapf: enable


# --- Widgets used in styling
# -----------------------------------------------------------------------------
class FrameContent(FrameBase):
    """Widget used in CSS styling."""


class LabelContentIcon(QLabel):
    """Label used in CSS styling."""


class LabelEmpty(LabelBase):
    """Label used in CSS styling."""


class LabelContentTitle(LabelBase):
    """Label used in CSS styling."""


class ButtonContentText(ButtonBase):
    """Label used in CSS styling."""

    sig_entered = Signal()
    sig_left = Signal()

    def enterEvent(self, event):
        """Override Qt method."""
        super(ButtonContentText, self).enterEvent(event)
        self.sig_entered.emit()

    def leaveEvent(self, event):
        """Override Qt method."""
        super(ButtonContentText, self).leaveEvent(event)
        self.sig_left.emit()

    def focusInEvent(self, event):
        """Override Qt method."""
        super(ButtonContentText, self).focusInEvent(event)
        self.sig_entered.emit()

    def focusOutEvent(self, event):
        """Override Qt method."""
        super(ButtonContentText, self).focusOutEvent(event)
        self.sig_left.emit()


class ButtonContentInformation(ButtonBase):
    """Button used in CSS styling."""


class FrameContentHeader(FrameBase):
    """Frame used in CSS styling."""


class FrameContentBody(FrameBase):
    """Label used in CSS styling."""


class FrameContentIcon(FrameBase):
    """Label used in CSS styling."""


class FrameContentHover(FrameBase):
    """Frame used in css styling with fade in and fade out effect."""

    sig_clicked = Signal()
    sig_entered = Signal()
    sig_left = Signal()

    def __init__(self, *args, **kwargs):
        """Frame used in css styling with fade in and fade out effect."""
        super(FrameContentHover, self).__init__(*args, **kwargs)

        self.current_opacity = 0
        self.max_frame = 100
        self.max_opacity = 0.95
        self.button_text = None
        self.label_icon = None
        self.label_text = None
        self.summary = ''

        # Widgets
        self.text_document = QTextDocument(self)
        self.timeline = QTimeLine(500)

        font = QFont()

        if sys.platform == 'darwin':
            font.setPointSize(12)
        elif os.name == 'nt':
            font.setPointSize(9)
        else:
            font.setPointSize(9)

        self.text_document.setDefaultFont(font)
        self.text_document.setMaximumBlockCount(5)
        self.text_document.setDocumentMargin(10)
        # Setup
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAutoFillBackground(True)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setMinimumSize(self.widget_size())
        self.timeline.setFrameRange(0, self.max_frame)

        # Signals
        self.timeline.frameChanged.connect(self.set_opacity)

    def set_opacity(self, val):
        """Set the opacity via timeline."""
        self.current_opacity = (val * 1.0 / self.max_frame) * self.max_opacity
        self.update()

    def widget_size(self):
        """Return hover frame size."""
        bheight = 40 if self.button_text is None else self.button_text.height()

        width = SASS_VARIABLES.WIDGET_CONTENT_TOTAL_WIDTH
        height = SASS_VARIABLES.WIDGET_CONTENT_TOTAL_HEIGHT
        padding = SASS_VARIABLES.WIDGET_CONTENT_PADDING
        margin = 0  # SASS_VARIABLES.WIDGET_CONTENT_MARGIN
        return QSize(
            width - 2 * (padding + margin), height - 2 * margin - bheight
        )

    def fade_in(self):
        """Fade in hover card with text."""
        self.raise_()
        self.timeline.stop()
        self.timeline.setDirection(QTimeLine.Forward)
        self.timeline.start()

    def fade_out(self):
        """Fade out hover card with text."""
        self.timeline.stop()
        self.timeline.setDirection(QTimeLine.Backward)
        self.timeline.start()

    def enterEvent(self, event):
        """Override Qt method."""
        super(FrameContentHover, self).enterEvent(event)
        self.fade_in()
        self.sig_entered.emit()

    def leaveEvent(self, event):
        """Override Qt method."""
        super(FrameContentHover, self).leaveEvent(event)
        self.fade_out()
        self.sig_left.emit()

    def mousePressEvent(self, event):
        """Override Qt method."""
        self.sig_clicked.emit()

    def paintEvent(self, event):
        """Override Qt method."""
        painter = QPainter(self)
        painter.setOpacity(self.current_opacity)

        max_width = (
            SASS_VARIABLES.WIDGET_CONTENT_TOTAL_WIDTH -
            2 * SASS_VARIABLES.WIDGET_CONTENT_PADDING -
            2 * SASS_VARIABLES.WIDGET_CONTENT_MARGIN
        )

        # Hover top
        br = self.label_icon.rect().bottomRight()
        tl = self.label_icon.rect().topLeft() + QPoint(1, 1)
        y = br.y() + self.label_text.height() - 2
        #        br_new = QPoint(br.x() + 2, y) - QPoint(1, 1)
        br_new = QPoint(max_width - 1, y) - QPoint(1, 1)
        rect_hover = QRect(tl, br_new)  # 2 is the border

        pen = QPen(Qt.NoPen)
        brush = QBrush(Qt.SolidPattern)
        brush.setColor(QColor('#fff'))
        painter.setBrush(brush)
        painter.setPen(pen)
        painter.drawRect(rect_hover)

        font = self.font()
        font.setPointSize(10)
        painter.setFont(font)
        pen = QPen()
        pen.setColor(QColor('black'))
        painter.setPen(pen)
        td = self.text_document
        td.setPageSize(QSizeF(rect_hover.size()))
        td.setHtml(self.summary)
        td.drawContents(painter)

        self.raise_()


def split_text(text, widget, max_width, max_lines=3):
    """Split text in lines according to the widget forn metrics and width."""
    fm = widget.fontMetrics()
    words, lines = [], []

    for word in text.split():
        words.append(word)
        cum_width = fm.width(' '.join(words))
        if cum_width > max_width:
            words.pop()
            lines.append(words)
            words = [word]

    if words:
        lines.append(words)

    if len(lines) > max_lines:
        trimmed_lines = lines[:max_lines]
        trimmed_lines[-1][-1] = '...'  # Replace the last word with ...
    else:
        trimmed_lines = lines

    line_breaks = max_lines - len(trimmed_lines)
    if line_breaks > 0:
        trimmed_lines.append(['\n' * line_breaks])

    text = ''
    for line in trimmed_lines:
        text += ' '.join(line) + '\n'
    return text


# --- Main widgets
# -----------------------------------------------------------------------------
class ListWidgetContent(ListWidgetBase):
    """List Widget holding available videos in the learning tab."""

    sig_view_video = Signal(str, str)

    def __init__(self, *args, **kwargs):
        """List Widget holding available videos in the learning tab."""
        self._main = kwargs.pop('main', None)  # FIXME:
        super(ListWidgetContent, self).__init__(*args, **kwargs)
        self.tracker = GATracker()
        self.setViewMode(QListWidget.IconMode)

    def ordered_widgets(self):
        """Return a list of the ordered widgets."""
        ordered_widgets = []
        for item in self.items():
            ordered_widgets += item.ordered_widgets()
        return ordered_widgets

    def setup_item(self, item):
        """Override base method."""
        max_width = (
            SASS_VARIABLES.WIDGET_CONTENT_TOTAL_WIDTH -
            2 * SASS_VARIABLES.WIDGET_CONTENT_PADDING -
            2 * SASS_VARIABLES.WIDGET_CONTENT_MARGIN
        )
        uri = item.uri
        title = item.title

        item.button_text.clicked.connect(lambda: self.launch(uri, title))
        item.button_text.sig_entered.connect(
            lambda: item.frame_hover.fade_in()
        )
        item.button_text.sig_entered.connect(lambda: self.scroll_to_item(item))
        item.button_text.sig_left.connect(lambda: item.frame_hover.fade_out())
        item.frame_hover.sig_clicked.connect(lambda: self.launch(uri, title))
        item.frame_hover.sig_clicked.connect(
            lambda: item.button_text.setFocus()
        )
        item.widget.setStyleSheet(self.style_sheet)
        item.label_text.setText(
            '\n' + split_text(title, item.label_text, max_width)
        )

    def launch(self, uri, title):
        """Emit signal with youtube video identifier string."""
        qurl = QUrl(uri)
        QDesktopServices.openUrl(qurl)
        self.tracker.track_event('content', 'click', uri)
        self.sig_view_video.emit(uri, title)


class ListItemContent(ListWidgetItemBase):
    """Widget to build an item for the content listing."""

    def __init__(
        self,
        title='',
        description='',
        uri='',
        authors=None,
        venue='',
        path='',
        year='',
        summary='',
        banner='',
        tags='',
        subtitle='',
        date='',
        pixmap=None
    ):
        """Widget to build an item for the content listing."""
        super(ListItemContent, self).__init__()

        self.title = title
        self.uri = uri
        self.authors = authors if authors else []
        self.venue = venue
        self.banner = banner
        self.year = year
        self.path = path
        self.tags = tags
        self.subtitle = subtitle
        self.date = date
        self.summary = summary
        self.timer_pixmap = QTimer()
        self.pixmaps = {}
        self.pixmap = pixmap
        self.label = None

        # Widgets
        self.widget = FrameContent()
        self.frame_hover = FrameContentHover(parent=self.widget)
        self.frame_body = FrameContentBody(parent=self.widget)
        self.frame_icon = FrameContentIcon(parent=self.widget)
        self.label_icon = LabelContentIcon(parent=self.widget)
        self.label_text = LabelContentTitle(parent=self.widget)
        self.button_text = ButtonContentText()

        # Widget setup
        self.button_text.setDefault(True)
        self.button_text.setAutoDefault(True)
        self.frame_hover.move(QPoint(5, 5))
        self.frame_hover.label_icon = self.label_icon
        self.frame_hover.label_text = self.label_text
        self.frame_hover.button_text = self.button_text

        valid_tags = {
            'documentation': 'Read',
            'webinar': "Explore",
            'event': "Learn More",
            'video': "View",
            'training': "Explore",
            'forum': "Explore",
            'social': "Engage"
        }
        self.tag = 'notag'
        filter_tags = []
        if len(tags) >= 1:
            filter_tags = [t.lower() for t in tags if t.lower() in valid_tags]
            if filter_tags:
                self.tag = filter_tags[0].lower()

        self.widget.setObjectName(self.tag)
        self.button_text.setObjectName(self.tag)
        self.button_text.setText(valid_tags.get(self.tag, ''))
        self.label_icon.setAlignment(Qt.AlignHCenter)
        self.timer_pixmap.setInterval(random.randint(950, 1050))

        if pixmap:
            self.update_thumbnail(pixmap=pixmap)

        # Layout
        if title:
            layout_icon = QVBoxLayout()
            layout_icon_h = QHBoxLayout()
            layout_icon_h.addWidget(self.label_icon)
            layout_icon.addStretch()
            layout_icon.addLayout(layout_icon_h)
            layout_icon.addStretch()
            self.frame_icon.setLayout(layout_icon)

            layout_frame = QVBoxLayout()
            layout_frame.addWidget(self.frame_icon)
            layout_frame.addStretch()
            layout_frame.addWidget(self.label_text)
            layout_frame.addStretch()
            layout_frame.addWidget(self.button_text)
            self.frame_body.setLayout(layout_frame)

            layout = QVBoxLayout()
            layout.addWidget(self.frame_body)
            self.widget.setLayout(layout)
            self.setSizeHint(self.widget_size())
            self.widget.setMinimumSize(self.widget_size())

        if summary:
            date = '<small>' + date + '</small><br>' if date else ''
            sub = '<small>' + subtitle + '</small><br>' if subtitle else ''
            tt = (
                '<p><b>' + title + '</b><br>' + sub + date + summary + '</p>'
            )
            self.frame_hover.summary = tt
        else:
            self.frame_hover.summary = '<p><b>' + title + '</b><br>'

        # Signals
        self.frame_hover.sig_entered.connect(
            lambda: self.label_text.setProperty('active', True)
        )
        self.frame_hover.sig_left.connect(
            lambda: self.label_text.setProperty('active', False)
        )
        self.frame_hover.sig_entered.connect(
            lambda: self.button_text.setProperty('active', True)
        )
        self.frame_hover.sig_left.connect(
            lambda: self.button_text.setProperty('active', False)
        )
        self.timer_pixmap.timeout.connect(self.update_thumbnail)

        # Setup
        self.timer_pixmap.start()

    def ordered_widgets(self):
        """Return a list of the ordered widgets."""
        return [self.button_text]

    def show_information(self):
        """Display additional information of item."""
        if self.label:
            self.label.move(-1000, 0)
            self.label.show()
            app = QApplication.instance()
            geo = app.desktop().screenGeometry(self.button_information)
            w, h = geo.right(), geo.bottom()
            pos = self.button_information.mapToGlobal(QPoint(0, 0))
            x, y = pos.x() + 10, pos.y() + 10
            x = min(x, w - self.label.width())
            y = min(y, h - self.label.height())
            self.label.move(x, y)

    @staticmethod
    def widget_size():
        """Return the size defined in the SASS file."""
        return QSize(
            SASS_VARIABLES.WIDGET_CONTENT_TOTAL_WIDTH,
            SASS_VARIABLES.WIDGET_CONTENT_TOTAL_HEIGHT
        )

    def update_thumbnail(self, pixmap=None):
        """Update thumbnails image."""
        height = SASS_VARIABLES.WIDGET_CONTENT_TOTAL_HEIGHT / 2
        image_width = (
            SASS_VARIABLES.WIDGET_CONTENT_TOTAL_WIDTH -
            2 * SASS_VARIABLES.WIDGET_CONTENT_PADDING -
            2 * SASS_VARIABLES.WIDGET_CONTENT_MARGIN
        )
        # image_height = height * 1.666 if 'video' in self.tag else height
        pixmap = self.pixmaps.get(self.path)
        if pixmap and not pixmap.isNull():
            self.pixmap = pixmap
            pix_width = self.pixmap.width()
            pix_height = self.pixmap.height()
            if pix_width * 1.0 / pix_height < image_width * 1.0 / height:
                max_height = height
                max_width = height * (pix_width / pix_height)
            else:
                max_height = image_width * (pix_height / pix_width)
                max_width = image_width

            self.label_icon.setScaledContents(True)
            self.label_icon.setMaximumWidth(max_width)
            self.label_icon.setMaximumHeight(max_height)
            self.label_icon.setPixmap(self.pixmap)
            self.timer_pixmap.stop()


# --- Local testing
# -----------------------------------------------------------------------------
def local_test():  # pragma: no cover
    """Run local test."""
    from anaconda_navigator.utils.py3compat import to_text_string
    from anaconda_navigator.utils.qthelpers import qapplication

    app = qapplication(test_time=5)
    widget = ListWidgetContent()
    widget.show()
    for i in range(10):
        item = ListItemContent(
            title='Title ' + str(i),
            description='Description',
            summary='Summary',
            tags=['social'],
            subtitle='subtitle',
            uri=to_text_string(i)
        )
        widget.addItem(item)
    widget.update_style_sheet()
    app.exec_()


if __name__ == "__main__":  # pragma: no cover
    local_test()
