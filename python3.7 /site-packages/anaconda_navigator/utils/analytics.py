# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""
Google analytics tracker utilities.

Pages
-----

/home
/community
/environments

/environments/create
/environments/clone
/environments/remove
/login
/about

"""

# yapf: disable

# Standard library imports
from collections import deque
import hashlib
import locale
import platform
import sys

# Third party imports
from qtpy.QtCore import QObject, QThread, QTimer, Signal
from qtpy.QtWidgets import QDesktopWidget
import requests

# Local imports
from anaconda_navigator import __version__ as app_version
from anaconda_navigator.api.anaconda_api import AnacondaAPI
from anaconda_navigator.config import CONF
from anaconda_navigator.external.UniversalAnalytics import Tracker
from anaconda_navigator.utils.encoding import ensure_binary
from anaconda_navigator.utils.logs import logger


# yapf: enable

try:
    from qtpy.QtCore import __version__ as QT_VERSION
except ImportError:
    from qtpy.QtCore import QT_VERSION_STR as QT_VERSION


class AnalyticsWorker(QObject):
    """Google analytics tracker worker."""

    sig_finished = Signal(object, object, object)

    def __init__(self, method, args, kwargs):
        """Google analytics tracker worker."""
        super(AnalyticsWorker, self).__init__()
        self.method = method
        self.args = args
        self.kwargs = kwargs
        self._is_finished = False

    def is_finished(self):
        """Return True if the worker process has finished, otherwise False."""
        return self._is_finished

    def start(self):
        """Start the worker process."""
        error = None
        output = None
        try:
            output = self.method(*self.args, **self.kwargs)
        except Exception as err:
            error = err
            module = getattr(self.method, '__module__', '')
            method_name = getattr(self.method, '__name__', '')
            logger.debug(str((module, method_name, error)))

        self.sig_finished.emit(self, output, error)
        self._is_finished = True


class _GATracker(object):
    """Google analytics tracker."""

    TRACKER_ID = 'UA-27761864-8'

    def __init__(self):
        """Google analytics tracker."""
        # Avoid blocking the UI
        self._queue = deque()
        self._threads = []
        self._workers = []
        self._timer = QTimer()
        self.api = AnacondaAPI()

        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._clean)

        self.setup()

    def setup(self):
        """Setup the tracker initial configuration."""
        # Set tracker config
        try:
            user = self.api.client_user().get('login', '@anonymous')
        except Exception:
            user = '@anonymous'

        domain = self.api.client_domain()
        normalized_user = domain + '/' + user
        hashed_user = hashlib.md5(ensure_binary(normalized_user)).hexdigest()

        self.tracker = Tracker.create(
            self.TRACKER_ID,
            client_id=hashed_user,
            user_id=hashed_user,
        )
        pkg_version = self.api.conda_package_version

        # Set custom variables
        python_version = '.'.join([str(i) for i in sys.version_info[:3]])
        operating_system = ";".join(
            [platform.uname()[0]] + list(platform.uname()[2:]),
        )
        pyqt_version = (
            pkg_version(pkg='pyqt5', name='root')
            or pkg_version(pkg='pyqt4', name='root')
            or pkg_version(pkg='pyqt', name='root')
        )
        conda_version = pkg_version(pkg='conda', name='root')

        # Track initial global data events
        self.track_event('application', 'python-version', label=python_version)
        self.track_event('application', 'language', label=self.get_language())
        self.track_event(
            'application',
            'screen-resolution',
            label=self.get_screen_resolution()
        )
        self.track_event(
            'application', 'operating-system', label=operating_system
        )
        self.track_event('application', 'version', label=app_version)
        self.track_event(
            'application', 'platform', label=self.api.conda_platform()
        )
        self.info = {
            'python': python_version,
            'language': self.get_language(),
            'os': operating_system,
            'version': app_version,
            'platform': self.api.conda_platform(),
            'qt': QT_VERSION,
            'pyqt': pyqt_version,
            'conda': conda_version
        }

    def _clean(self):
        """Check for inactive workers and remove their references."""
        if self._workers:
            for w in self._workers:
                if w.is_finished():
                    self._workers.remove(w)

        if self._threads:
            for t in self._threads:
                if t.isFinished():
                    self._threads.remove(t)
        else:
            self._timer.stop()

    def _start(self):
        """Start the next item in the worker queue."""
        if len(self._queue) == 1:
            thread = self._queue.popleft()
            thread.start()
            self._timer.start()

    def _create_worker(self, method, *args, **kwargs):
        """Create a worker for this client to be run in a separate thread."""
        provide_analytics = CONF.get('main', 'provide_analytics')

        thread = QThread()
        worker = AnalyticsWorker(method, args, kwargs)

        if provide_analytics:
            worker.moveToThread(thread)
            worker.sig_finished.connect(self._start)
            worker.sig_finished.connect(thread.quit)
            thread.started.connect(worker.start)
            self._queue.append(thread)
            self._threads.append(thread)
            self._workers.append(worker)
            self._start()

        return worker

    def track_event(self, category, action, label=None):
        """Track analytyics event."""
        return self._create_worker(
            self.tracker.send,
            'event',
            category=category,
            action=action,
            label=str(label),
            anonymizeIp=True,
        )

    def track_page(self, page, pagetitle=None):
        """
        Track analytyics page.

        Page in the context of Navigator is a tab, a dialog, a message box.
        """
        if pagetitle is None:
            title = ' '.join([i for i in page.split('/') if i])
        else:
            title = pagetitle

        title = title.capitalize()
        return self._create_worker(
            self.tracker.send,
            'pageview',
            page=page,
            pagetitle=title,
            anonymizeIp=True,
        )

    def set_client_id(self, client_id=None):
        """Set the client tracker ID."""
        self.tracker = Tracker.create(
            'UA-74661388-1', client_id=client_id, user_id=client_id
        )

    def get_ip(self):
        """
        Return the current ip based on ipify.org.

        This method is used for testing not for collecting actual ip addresses.
        """
        try:
            response = requests.get(
                'https://api.ipify.org/?format=json',
                proxies=self.api.conda_load_proxy_config()
            )
            ip = response.json()['ip']
        except Exception as error:
            logger.error(str(error))
            ip = None

        return ip

    @staticmethod
    def get_language():
        """Return the locale language."""
        # Process locale language
        try:
            lang = locale.getdefaultlocale()[0]
        except Exception:
            lang = None

        if not lang:
            lang = 'en'

        return lang

    @staticmethod
    def get_screen_resolution():
        """Return the screen resolution of the primary screen."""
        try:
            widget = QDesktopWidget()
            geometry = widget.availableGeometry(widget.primaryScreen())
            value = "{0}x{1}".format(geometry.width(), geometry.height())
        except Exception:
            value = None
        return value


GA_TRACKER = None


def GATracker():
    """Google Analytics Tracker."""
    global GA_TRACKER

    if GA_TRACKER is None:
        GA_TRACKER = _GATracker()

    return GA_TRACKER


# --- Local testing
# -----------------------------------------------------------------------------
def print_test(worker, output, error):  # pragma: no cover
    """Print test output from worker."""
    print(output, error)


def local_test():  # pragma: no cover
    """Main local test."""
    from anaconda_navigator.utils.qthelpers import qapplication
    app = qapplication()
    tracker = GATracker()
    worker = tracker.track_page('/home')
    worker.sig_finished.connect(print_test)
    print(worker)
    print(tracker.get_screen_resolution())
    print(tracker.get_language())
    app.exec_()


if __name__ == '__main__':  # pragma: no cover
    local_test()
