# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Splash screen and intial startup splash."""

# yapf: disable

from __future__ import absolute_import, division, print_function

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QPixmap
from qtpy.QtWidgets import (QApplication, QCheckBox, QGraphicsOpacityEffect,
                            QHBoxLayout, QLabel, QSplashScreen, QVBoxLayout)

# Local imports
from anaconda_navigator.config import CONF
from anaconda_navigator.static.images import (ANACONDA_ICON_256_PATH,
                                              ANACONDA_NAVIGATOR_LOGO)
from anaconda_navigator.widgets import (ButtonNormal, ButtonPrimary,
                                        QSvgWidget, SpacerHorizontal,
                                        SpacerVertical)
from anaconda_navigator.widgets.dialogs import DialogBase


# yapf: enable


class SplashScreen(QSplashScreen):
    """Splash screen for the main window."""

    def __init__(self, *args, **kwargs):
        """Splash screen for the main window."""
        super(SplashScreen, self).__init__(*args, **kwargs)
        self._effect = QGraphicsOpacityEffect()
        self._font = self.font()
        self._pixmap = QPixmap(ANACONDA_ICON_256_PATH)
        self._message = ''

        # Setup
        self._font.setPixelSize(10)
        self._effect.setOpacity(0.9)
        self.setFont(self._font)
        self.setGraphicsEffect(self._effect)
        self.setPixmap(self._pixmap)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.SplashScreen | Qt.WindowStaysOnTopHint
        )

    def get_message(self):
        """Return currently displayed message."""
        return self._message

    def show_message(self, message):
        """Show message in the screen."""
        self._message = message
        message += '\n'
        self.show()
        self.showMessage(
            message, Qt.AlignBottom | Qt.AlignCenter | Qt.AlignAbsolute,
            QColor(Qt.white)
        )
        QApplication.processEvents()


class FirstSplash(DialogBase):
    """Startup splash to display the first time that Navigator runs."""

    def __init__(self, parent=None):
        """Startup splash to display the first time that Navigator runs."""
        super(FirstSplash, self).__init__(parent=parent)

        text = """
        Thanks for installing Anaconda!

        Anaconda Navigator helps you easily start important Python applications
        and manage the packages in your local Anaconda installation. It also
        connects you to online resources for learning and engaging with the
        Python, SciPy, and PyData community.

        To help us improve Anaconda Navigator, fix bugs, and make it even
        easier for everyone to use Python, we gather anonymized usage
        information, just like most web browsers and mobile apps.

        To opt out of this, please uncheck below (You can always change this
        setting in the Preferences menu).
        """
        # Variables
        self.config = CONF

        # Widgets
        self.button_ok = ButtonNormal('Ok')
        self.button_ok_dont_show = ButtonPrimary("Ok, and don't show again")
        self.checkbox_track = QCheckBox(
            "Yes, I'd like to help improve "
            "Anaconda."
        )
        self.label_about = QLabel(text)
        self.widget_icon = QSvgWidget(ANACONDA_NAVIGATOR_LOGO)

        # Widget setup
        self.frame_title_bar.hide()
        self.widget_icon.setFixedSize(self.widget_icon.size_for_width(400))

        # Layouts
        layout_buttons = QHBoxLayout()
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.button_ok)
        layout_buttons.addWidget(SpacerHorizontal())
        layout_buttons.addWidget(self.button_ok_dont_show)

        layout = QVBoxLayout()
        layout.addWidget(self.widget_icon, 0, Qt.AlignCenter)
        layout.addWidget(self.label_about)
        layout.addWidget(self.checkbox_track, 0, Qt.AlignCenter)
        layout.addWidget(SpacerVertical())
        layout.addWidget(SpacerVertical())
        layout.addLayout(layout_buttons)
        self.setLayout(layout)

        # Signals
        self.button_ok.clicked.connect(lambda: self.accept(show_startup=True))
        self.button_ok_dont_show.clicked.connect(
            lambda: self.accept(show_startup=False)
        )

        self.setup()

    def setup(self):
        """Setup widget content."""
        provide_analytics = self.config.get('main', 'provide_analytics')
        self.checkbox_track.setChecked(provide_analytics)

    def accept(self, show_startup):
        """Override Qt method."""
        provide_analytics = self.checkbox_track.checkState() == Qt.Checked
        self.config.set('main', 'provide_analytics', provide_analytics)
        self.config.set('main', 'show_startup', show_startup)
        DialogBase.accept(self)

    def reject(self):
        """
        Override Qt method.

        Force user to select one of the two options bellow and disalow
        canceling the dialog (pressing escape)
        """
        pass


# --- Local testing
# -----------------------------------------------------------------------------
def local_test():  # pragma: no cover
    """Run local test."""
    from anaconda_navigator.utils.qthelpers import qapplication

    app = qapplication()
    widget_splash = SplashScreen()
    widget_splash.show_message('Initializing...')
    widget_splash.show()

    widget_first_splash = FirstSplash()
    widget_first_splash.show()
    widget_first_splash.update_style_sheet()
    app.exec_()


if __name__ == '__main__':  # pragma: no cover
    local_test()
