# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Project API."""

# Standard library imports
from collections import deque
import sys

# Third party imports
from qtpy.QtCore import QObject, QThread, QTimer, Signal

# Local imports
from anaconda_navigator.utils.logs import logger


class ProjectWorker(QObject):
    """Project Worker based on cona-kapsel."""

    sig_finished = Signal(object, object, object)

    def __init__(self, method, args, kwargs):
        """Anaconda Project Worker."""
        super(ProjectWorker, self).__init__()
        self.method = method
        self.args = args
        self.kwargs = kwargs
        self._is_finished = False

    def is_finished(self):
        """Return True if worker status is finished otherwise return False."""
        return self._is_finished

    def start(self):
        """Start process worker for given method args and kwargs."""
        error = None
        output = None

        try:
            output = self.method(*self.args, **self.kwargs)
        except Exception as err:
            error = err
            logger.debug(str((self.method.__name__, error)))

        self.sig_finished.emit(self, output, error)
        self._is_finished = True


class _ProjectAPIWrapper(QObject):
    """Project API based on conda-kapsel."""

    MAX_THREADS = 1

    def __init__(self):
        """Project API based on anaconda-project."""
        super(QObject, self).__init__()
        try:
            from anaconda_project.api import AnacondaProject
            self._project_api = AnacondaProject()
        except ImportError:
            self._project_api = {}

        self._queue = deque()
        self._queue_workers = deque()
        self._threads = []
        self._workers = []
        self._timer = QTimer()
        self._timer_worker_delete = QTimer()
        self._running_threads = 0
        self._bag_collector = deque()  # Keeps references to old workers

        self._chunk_size = 1024
        self._timer.setInterval(333)
        self._timer.timeout.connect(self._start)
        self._timer_worker_delete.setInterval(5000)
        self._timer_worker_delete.timeout.connect(self._clean_workers)

    def _clean_workers(self):
        """Delete periodically workers in workers bag."""
        while self._bag_collector:
            self._bag_collector.popleft()
        self._timer_worker_delete.stop()

    def _start(self):
        """Start threads and check for inactive workers."""
        if self._queue_workers and self._running_threads < self.MAX_THREADS:
            # print('Queue: {0} Running: {1} Workers: {2} '
            #       'Threads: {3}'.format(len(self._queue_workers),
            #                                 self._running_threads,
            #                                 len(self._workers),
            #                                 len(self._threads)))
            self._running_threads += 1
            thread = QThread()
            worker = self._queue_workers.popleft()
            worker.moveToThread(thread)
            worker.sig_finished.connect(thread.quit)
            thread.started.connect(worker.start)
            thread.start()
            self._threads.append(thread)

        if self._workers:
            for w in self._workers:
                if w.is_finished():
                    self._bag_collector.append(w)
                    self._workers.remove(w)

        if self._threads:
            for t in self._threads:
                if t.isFinished():
                    self._threads.remove(t)
                    self._running_threads -= 1

        if len(self._threads) == 0 and len(self._workers) == 0:
            self._timer.stop()
            self._timer_worker_delete.start()

    def _create_worker(self, method, *args, **kwargs):
        """Create a new worker instance."""
        worker = ProjectWorker(method, args, kwargs)
        self._workers.append(worker)
        self._queue_workers.append(worker)
        self._timer.start()
        return worker

    def create_project(
        self,
        path,
        make_directory=False,
        name=None,
        icon=None,
        description=None
    ):
        """Initialize project given by path."""
        logger.debug(str((path)))
        method = self._project_api.create_project
        return self._create_worker(
            method,
            path,
            make_directory=make_directory,
            name=name,
            icon=icon,
            description=description,
        )

    def load_project(self, path):
        """Load project given by path."""
        logger.debug(str((path)))
        try:
            proj = self._project_api.load_project(path)
        except Exception:
            proj = self._project_api.load_project(path, frontend=None)

        return proj

    def upload(
        self, project, site=None, username=None, token=None, log_level=None
    ):
        """Upload project to repo."""
        logger.debug(str((project, site, username)))
        method = self._project_api.upload
        return self._create_worker(
            method,
            project,
            site=None,
            username=None,
            token=None,
            log_level=None
        )


PROJECT_API = None


def ProjectAPI():
    global PROJECT_API

    if PROJECT_API is None:
        PROJECT_API = _ProjectAPIWrapper()

    return PROJECT_API


def local_test():
    from anaconda_navigator.utils.qthelpers import qapplication
    app = qapplication()
    app.exec_(sys.exit)


if __name__ == '__main__':
    local_test()
