# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Worker threads for downloading files."""

# yapf: disable

# Standard library imports
from collections import deque
import json
import os
import sys

# Third party imports
from qtpy.QtCore import QBuffer, QByteArray, QObject, QThread, QTimer, Signal
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.packages.urllib3.util.retry import Retry
import requests

# Local imports
from anaconda_navigator.api.client_api import ClientAPI
from anaconda_navigator.api.conda_api import CondaAPI
from anaconda_navigator.utils.logs import logger
from anaconda_navigator.utils.py3compat import to_text_string


# yapf: enable

# In case verify is False, this prevents spamming the user console with
# messages
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def handle_qbytearray(obj, encoding):
    """Qt/Python3 compatibility helper."""
    if isinstance(obj, QByteArray):
        obj = obj.data()

    return to_text_string(obj, encoding=encoding)


class DownloadWorker(QObject):
    """Download Worker based on requests."""

    sig_chain_finished = Signal(object, object, object)
    sig_download_finished = Signal(str, str)
    sig_download_progress = Signal(str, str, int, int)
    sig_partial = Signal(object, object, object)
    sig_finished = Signal(object, object, object)

    def __init__(self, method, args, kwargs):
        """Download Worker based on requests."""
        super(DownloadWorker, self).__init__()
        self.method = method
        self.args = args
        self.kwargs = kwargs
        self._is_finished = False

    def _handle_partial(self, data):
        self.sig_partial.emit(self, data, None)

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
            print(err)
            error = err
            logger.debug(str((self.method.__name__, error)))

        self.sig_finished.emit(self, output, error)
        self._is_finished = True


class _DownloadAPI(QObject):
    """Download API based on requests."""

    _sig_download_finished = Signal(str, str)
    _sig_download_progress = Signal(str, str, int, int)
    _sig_partial = Signal(object)

    MAX_THREADS = 20
    DEFAULT_TIMEOUT = 5  # seconds

    def __init__(self, config=None):
        """Download API based on requests."""
        super(QObject, self).__init__()
        self._conda_api = CondaAPI()
        self._client_api = ClientAPI()
        self._config = config
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

    def _get_verify_ssl(self, verify, set_conda_ssl=True):
        """Get verify ssl."""
        if verify is None:
            verify_value = self._client_api.get_ssl(
                set_conda_ssl=set_conda_ssl,
            )
        else:
            verify_value = verify
        return verify_value

    def _is_internet_available(self):
        """Check initernet availability."""
        if self._config:
            config_value = self._config.get('main', 'offline_mode')
        else:
            config_value = False

        if config_value:
            connectivity = False
        else:
            connectivity = True  # is_internet_available()

        return connectivity

    @property
    def proxy_servers(self):
        """Return the proxy servers available from the conda rc config file."""
        return self._conda_api.load_proxy_config()

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
        worker = DownloadWorker(method, args, kwargs)
        self._workers.append(worker)
        self._queue_workers.append(worker)
        self._sig_download_finished.connect(worker.sig_download_finished)
        self._sig_download_progress.connect(worker.sig_download_progress)
        self._sig_partial.connect(worker._handle_partial)
        self._timer.start()
        return worker

    def _download(
        self,
        url,
        path=None,
        force=False,
        verify=None,
        chunked=True,
    ):
        """Callback for download."""
        verify_value = self._get_verify_ssl(verify, set_conda_ssl=False)

        if path is None:
            path = url.split('/')[-1]

        # Make dir if non existent
        folder = os.path.dirname(os.path.abspath(path))

        if not os.path.isdir(folder):
            os.makedirs(folder)

        # Get headers
        if self._is_internet_available():
            try:
                r = requests.head(
                    url,
                    proxies=self.proxy_servers,
                    verify=verify_value,
                    timeout=self.DEFAULT_TIMEOUT,
                )
                status_code = r.status_code
            except Exception as error:
                status_code = -1
                logger.error(str(error))

            logger.debug('Status code {0} - url'.format(status_code, url))

            if status_code != 200:
                logger.error('Invalid url {0}'.format(url))
                return path

            total_size = int(r.headers.get('Content-Length', 0))

            # Check if file exists
            if os.path.isfile(path) and not force:
                file_size = os.path.getsize(path)
            else:
                file_size = -1

            # print(path, total_size, file_size)

            # Check if existing file matches size of requested file
            if file_size == total_size:
                self._sig_download_finished.emit(url, path)
                return path
            else:
                try:
                    r = requests.get(
                        url,
                        stream=chunked,
                        proxies=self.proxy_servers,
                        verify=verify_value,
                        timeout=self.DEFAULT_TIMEOUT,
                    )
                    status_code = r.status_code
                except Exception as error:
                    status_code = -1
                    logger.error(str(error))

            # File not found or file size did not match. Download file.
            progress_size = 0
            bytes_stream = QBuffer()  # BytesIO was segfaulting for big files
            bytes_stream.open(QBuffer.ReadWrite)

            # For some chunked content the app segfaults (with big files)
            # so now chunked is a kwarg for this method
            if chunked:
                for chunk in r.iter_content(chunk_size=self._chunk_size):
                    # print(url, progress_size, total_size)
                    if chunk:
                        bytes_stream.write(chunk)
                        progress_size += len(chunk)
                        self._sig_download_progress.emit(
                            url,
                            path,
                            progress_size,
                            total_size,
                        )

                        self._sig_partial.emit(
                            {
                                'url': url,
                                'path': path,
                                'progress_size': progress_size,
                                'total_size': total_size,
                            }
                        )

            else:
                bytes_stream.write(r.content)

            bytes_stream.seek(0)
            data = bytes_stream.data()

            with open(path, 'wb') as f:
                f.write(data)

            bytes_stream.close()

        self._sig_download_finished.emit(url, path)

        return path

    def _is_valid_url(self, url, verify=None):
        """Callback for is_valid_url."""
        verify_value = self._get_verify_ssl(verify)

        if self._is_internet_available():
            try:
                r = requests.head(
                    url,
                    proxies=self.proxy_servers,
                    verify=verify_value,
                    timeout=self.DEFAULT_TIMEOUT,
                )
                value = r.status_code in [200]
            except Exception as error:
                logger.error(str(error))
                value = False

        return value

    def _is_valid_channel(
        self,
        channel,
        conda_url='https://conda.anaconda.org',
        verify=None,
    ):
        """Callback for is_valid_channel."""
        verify_value = self._get_verify_ssl(verify)

        if channel.startswith('https://') or channel.startswith('http://'):
            url = channel
        else:
            url = "{0}/{1}".format(conda_url, channel)

        if url[-1] == '/':
            url = url[:-1]

        plat = self._conda_api.get_platform()
        repodata_url = "{0}/{1}/{2}".format(url, plat, 'repodata.json')

        if self._is_internet_available():
            try:
                r = requests.head(
                    repodata_url,
                    proxies=self.proxy_servers,
                    verify=verify_value,
                    timeout=self.DEFAULT_TIMEOUT,
                )
                value = r.status_code in [200]
            except Exception as error:
                logger.error(str(error))
                value = False

        return value

    def _is_valid_api_url(self, url, verify=None):
        """Callback for is_valid_api_url."""
        verify_value = self._get_verify_ssl(verify)

        # Check response is a JSON with ok: 1
        data = {}

        if verify is None:
            verify_value = self._client_api.get_ssl()
        else:
            verify_value = verify

        if self._is_internet_available():
            try:
                r = requests.get(
                    url,
                    proxies=self.proxy_servers,
                    verify=verify_value,
                    timeout=self.DEFAULT_TIMEOUT,
                )
                content = to_text_string(r.content, encoding='utf-8')
                data = json.loads(content)
            except Exception as error:
                logger.error(str(error))

        return data.get('ok', 0) == 1

    def _get_url(self, url, as_json=False, verify=None):
        """Callback for url checking."""
        data = {}
        verify_value = self._get_verify_ssl(verify)

        if self._is_internet_available():
            try:
                # See: https://github.com/ContinuumIO/navigator/issues/1485
                session = requests.Session()
                retry = Retry(connect=3, backoff_factor=0.5)
                adapter = HTTPAdapter(max_retries=retry)
                session.mount('http://', adapter)
                session.mount('https://', adapter)

                r = session.get(
                    url,
                    proxies=self.proxy_servers,
                    verify=verify_value,
                    timeout=self.DEFAULT_TIMEOUT,
                )
                data = to_text_string(r.content, encoding='utf-8')

                if as_json:
                    data = json.loads(data)

            except Exception as error:
                logger.error(str(error))

        return data

    def _get_api_info(self, url, verify=None):
        """Callback."""
        verify_value = self._get_verify_ssl(verify)
        data = {
            "api_url": url,
            "api_docs_url": "https://api.anaconda.org/docs",
            "conda_url": "https://conda.anaconda.org/",
            "main_url": "https://anaconda.org/",
            "pypi_url": "https://pypi.anaconda.org/",
            "swagger_url": "https://api.anaconda.org/swagger.json",
        }
        if self._is_internet_available():
            try:
                r = requests.get(
                    url,
                    proxies=self.proxy_servers,
                    verify=verify_value,
                    timeout=self.DEFAULT_TIMEOUT,
                )
                content = to_text_string(r.content, encoding='utf-8')
                new_data = json.loads(content)
                data['conda_url'] = new_data.get(
                    'conda_url', data['conda_url']
                )
            except Exception as error:
                logger.error(str(error))

        return data

    # --- Public API
    # -------------------------------------------------------------------------
    def download(self, url, path=None, force=False, verify=None, chunked=True):
        """Download file given by url and save it to path."""
        logger.debug(str((url, path, force)))
        method = self._download
        return self._create_worker(
            method,
            url,
            path=path,
            force=force,
            verify=verify,
            chunked=chunked,
        )

    def terminate(self):
        """Terminate all workers and threads."""
        for t in self._threads:
            t.quit()
        self._thread = []
        self._workers = []

    def is_valid_url(self, url, non_blocking=True):
        """Check if url is valid."""
        logger.debug(str((url)))
        if non_blocking:
            method = self._is_valid_url
            return self._create_worker(method, url)
        else:
            return self._is_valid_url(url)

    def is_valid_api_url(self, url, non_blocking=True, verify=None):
        """Check if anaconda api url is valid."""
        logger.debug(str((url)))
        if non_blocking:
            method = self._is_valid_api_url
            return self._create_worker(method, url, verify=verify)
        else:
            return self._is_valid_api_url(url=url, verify=verify)

    def is_valid_channel(
        self,
        channel,
        conda_url='https://conda.anaconda.org',
        non_blocking=True,
    ):
        """Check if a conda channel is valid."""
        logger.debug(str((channel, conda_url)))
        if non_blocking:
            method = self._is_valid_channel
            return self._create_worker(method, channel, conda_url)
        else:
            return self._is_valid_channel(channel, conda_url=conda_url)

    def get_url(self, url, as_json=False, verify=None, non_blocking=True):
        """Get url content."""
        logger.debug(str(url))
        if non_blocking:
            method = self._get_url
            return self._create_worker(
                method, url, as_json=as_json, verify=verify
            )
        else:
            return self._get_url(url, as_json=as_json, verify=verify)

    def get_api_info(self, url, non_blocking=True):
        """Query anaconda api info."""
        logger.debug(str((url, non_blocking)))
        if non_blocking:
            method = self._get_api_info
            return self._create_worker(method, url)
        else:
            return self._get_api_info(url)


DOWNLOAD_API = None


def DownloadAPI(config=None):
    """Download API threaded worker based on requests."""
    global DOWNLOAD_API

    if DOWNLOAD_API is None:
        DOWNLOAD_API = _DownloadAPI(config=config)

    return DOWNLOAD_API


# --- Local testing
# -----------------------------------------------------------------------------
def ready_print(worker, output, error):  # pragma: no cover
    """Print worker output for tests."""
    print(worker, output, error)


def local_test():  # pragma: no cover
    """Main local test."""
    from anaconda_navigator.utils.qthelpers import qapplication
    urls = [
        'https://repo.anaconda.com/pkgs/free/linux-64/repodata.json.bz2',
        'https://repo.anaconda.com/pkgs/free/linux-64/repodata.json.bz2',
        'https://conda.anaconda.org/anaconda/linux-64/repodata.json.bz2',
        'https://conda.anaconda.org/asmeurer/linux-64/repodata.json.bz2',
        'https://conda.anaconda.org/conda-forge/linux-64/repodata.json.bz2',
    ]
    path = os.sep.join([os.path.expanduser('~'), 'testing-download'])

    app = qapplication()
    api = DownloadAPI()
    urls += ['asdasdasdad']
    for i, url in enumerate(urls):
        worker = api.is_valid_url(url)
        worker.url = url
        worker.sig_finished.connect(ready_print)
        filepath = os.path.join(path, str(i) + '.json.bz2')
        worker = api.download(url, path=filepath, force=True)
        worker.sig_finished.connect(ready_print)

    api = DownloadAPI()
    print(api._is_valid_api_url('https://api.anaconda.org'))
    print(api._is_valid_api_url('https://conda.anaconda.org'))
    print(api._is_valid_channel('https://google.com'))
    print(api._is_valid_channel('https://conda.anaconda.org/continuumcrew'))
    print(api.get_api_info('https://api.anaconda.org'))
    sys.exit(app.exec_())


if __name__ == '__main__':  # pragma: no cover
    local_test()
