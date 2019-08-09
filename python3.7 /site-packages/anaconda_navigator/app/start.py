#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Application start."""

# yapf: disable

# Standard library imports
import os
import signal
import sys

# Third party imports
from qtpy import PYQT5
from qtpy.QtCore import QCoreApplication, QEvent, QObject, Qt
from qtpy.QtGui import QIcon

# Local imports
from anaconda_navigator.config import (CONF, LINUX, LOCKFILE, MAC, PIDFILE,
                                       UBUNTU)
from anaconda_navigator.external import filelock
from anaconda_navigator.static import images
from anaconda_navigator.static.fonts import load_fonts
from anaconda_navigator.utils import misc
from anaconda_navigator.utils.logs import clean_logs, setup_logger
from anaconda_navigator.utils.qthelpers import qapplication
from anaconda_navigator.widgets.dialogs import MessageBoxInformation
from anaconda_navigator.widgets.dialogs.splash import SplashScreen
from anaconda_navigator.widgets.main_window import MainWindow


# yapf: enable

# For retina displays on qt5
if CONF.get('main', 'enable_high_dpi_scaling'):
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)


def except_hook(cls, exception, traceback):
    """Custom except hook to avoid crashes on PyQt5."""
    sys.__excepthook__(cls, exception, traceback)


def set_application_icon():
    """Set application icon."""
    global app
    if LINUX and UBUNTU:
        app_icon = QIcon(images.ANACONDA_LOGO_WHITE)
    else:
        app_icon = QIcon(images.ANACONDA_LOGO)
    app.setWindowIcon(app_icon)


def run_app(splash):
    """Create and show Navigator's main window."""
    window = MainWindow(splash=splash, tab_project=False)
    # window.setup()
    return window


class EventEater(QObject):
    """Event filter for application state."""

    def __init__(self, app):
        """Event filter for application state."""
        super(EventEater, self).__init__()
        self.app = app

    def eventFilter(self, ob, event):
        """Qt override."""
        if (event.type() == QEvent.ApplicationActivate and MAC and
                self.app.window.setup_ready):
            self.app.window.show()
            if self.app.window.isMaximized():
                self.app.window.showMaximized()
            elif self.app.window.isFullScreen():
                self.app.window.showFullScreen()
            else:
                self.app.window.showNormal()
            return True

        return super(EventEater, self).eventFilter(ob, event)


def start_app(options):  # pragma: no cover
    """Main application entry point."""
    # Setup logger
    setup_logger(options.log_level)

    # Monkey patching sys.excepthook to avoid crashes in PyQt 5.5+
    if PYQT5:
        sys.excepthook = except_hook

    # Clean old style logs
    clean_logs()

    global app
    app = qapplication(test_time=60)
    set_application_icon()
    load_fonts(app)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Check if running as root or with sudo on Unix
    # print(os.environ.get('SUDO_UID', None))
    if (MAC or LINUX) and os.environ.get('SUDO_UID', None) is not None:
        msgbox = MessageBoxInformation(
            title="Anaconda Navigator Information",
            text=(
                "Anaconda Navigator cannot be run with root user "
                "privileges."
            )
        )
        sys.exit(msgbox.exec_())

    # Create file lock
    lock = filelock.FileLock(LOCKFILE)
    try:
        load_pid = misc.load_pid()

        # This means a PSutil Access Denied error was raised
        if load_pid is False:
            msgbox = MessageBoxInformation(
                title="Anaconda Navigator Startup Error",
                text=(
                    "Navigator failed to start due to an incorrect shutdown. "
                    "<br><br>"
                    "We were unable to remove the pid & lock files. "
                    "Please manually remove the following files and restart "
                    "Anaconda Navigator:<br><ul>"
                    "<li><pre>{}</pre></li><li><pre>{}</pre></li></ul>"
                    "".format(LOCKFILE, PIDFILE)
                )
            )
            sys.exit(msgbox.exec_())
        elif load_pid is None:  # A stale lock might be around
            misc.remove_lock()

        with lock.acquire(timeout=3.0):  # timeout in seconds
            misc.save_pid()
            splash = SplashScreen()
            splash.show_message("Initializing...")
            window = run_app(splash)
            app.window = window
            event_eater = EventEater(app)
            app.installEventFilter(event_eater)
            sys.exit(app.exec_())
    except filelock.Timeout:
        msgbox = MessageBoxInformation(
            title="Anaconda Navigator Information",
            text=(
                "There is an instance of "
                "Anaconda Navigator already "
                "running."
            )
        )
        sys.exit(msgbox.exec_())
