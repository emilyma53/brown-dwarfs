# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Worker threads for using the anaconda-client api."""

# Standard library imports
from collections import deque
from traceback import format_exc
import json
import logging
import re
import time

# Third party imports
from qtpy.QtCore import QObject, QThread, QTimer, Signal
import binstar_client
import requests

# Local imports
from anaconda_navigator.api.conda_api import CondaAPI
from anaconda_navigator.config import CONF, DEFAULT_BRAND
from anaconda_navigator.utils import constants as C
from anaconda_navigator.utils import sort_versions
from anaconda_navigator.utils.logs import logger
from anaconda_navigator.utils.misc import is_internet_available
from anaconda_navigator.utils.py3compat import is_text_string, to_text_string
from anaconda_navigator.widgets.dialogs import MessageBoxError


class ClientWorker(QObject):
    """Anaconda Client API process worker."""

    sig_chain_finished = Signal(object, object, object)
    sig_finished = Signal(object, object, object)

    def __init__(self, method, args, kwargs):
        """Anaconda Client API process worker."""
        super(ClientWorker, self).__init__()
        self.method = method
        self.args = args
        self.kwargs = kwargs
        self._is_finished = False

    def is_finished(self):
        """Return wether or not the worker has finished running the task."""
        return self._is_finished

    def start(self):
        """Start the worker process."""
        error, output = None, None
        try:
            time.sleep(0.1)
            output = self.method(*self.args, **self.kwargs)
        except Exception as err:
            logger.debug(
                str((self.method.__module__, self.method.__name__, err)),
            )
            error = str(err)
            error = error.replace('(', '')
            error = error.replace(')', '')

        self.sig_finished.emit(self, output, error)
        self._is_finished = True


class Args:
    """Dummy class to pass to anaconda client on token loading and removal."""


class _ClientAPI(QObject):
    """Anaconda Client API wrapper."""

    DEFAULT_TIMEOUT = 6

    def __init__(self, config=None):
        """Anaconda Client API wrapper."""
        super(QObject, self).__init__()
        self._conda_api = CondaAPI()
        self._anaconda_client_api = None
        self._config = config
        self._queue = deque()
        self._threads = []
        self._workers = []
        self._timer = QTimer()
        self.config = CONF

        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._clean)

        # Setup
        self.reload_binstar_client()

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
        """Take avalaible worker from the queue and start it."""
        if len(self._queue) == 1:
            thread = self._queue.popleft()
            thread.start()
            self._timer.start()

    def _create_worker(self, method, *args, **kwargs):
        """Create a worker for this client to be run in a separate thread."""
        # FIXME: this might be heavy...
        thread = QThread()
        worker = ClientWorker(method, args, kwargs)
        worker.moveToThread(thread)
        worker.sig_finished.connect(self._start)
        worker.sig_finished.connect(thread.quit)
        thread.started.connect(worker.start)
        self._queue.append(thread)
        self._threads.append(thread)
        self._workers.append(worker)
        self._start()
        return worker

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

    # --- Callbacks
    # -------------------------------------------------------------------------
    @staticmethod
    def _load_repodata(repodata, metadata=None, python_version=None):
        """
        Load all the available package information.

        See load_repadata for full documentation.
        """
        metadata = metadata if metadata else {}
        # python_version = '.'.join(python_version.split('.')[:2])

        all_packages = {}
        for channel_url, data in repodata.items():
            packages = data.get('packages', {})

            for canonical_name in packages:
                data = packages[canonical_name]
                # Do not filter based on python version
                # if (python_version and not is_dependency_met(
                #         data['depends'], python_version, 'python')):
                #     continue
                name, version, b = tuple(canonical_name.rsplit('-', 2))

                if name not in all_packages:
                    all_packages[name] = {
                        'versions': set(),
                        'size': {},
                        'type': {},
                        'app_entry': {},
                        'app_type': {},
                    }
                elif name in metadata:
                    temp_data = all_packages[name]
                    temp_data['home'] = metadata[name].get('home', '')
                    temp_data['license'] = metadata[name].get('license', '')
                    temp_data['summary'] = metadata[name].get('summary', '')
                    temp_data['latest_version'] = metadata[name].get('version')
                    all_packages[name] = temp_data

                all_packages[name]['versions'].add(version)
                all_packages[name]['size'][version] = data.get('size', '')

                # Only the latest builds will have the correct metadata for
                # apps, so only store apps that have the app metadata
                if data.get('type'):
                    all_packages[name]['type'][version] = data.get('type')
                    all_packages[name]['app_entry'][version
                                                    ] = data.get('app_entry')
                    all_packages[name]['app_type'][version
                                                   ] = data.get('app_type')

        # Calculate the correct latest_version
        for name in all_packages:
            versions = tuple(
                sorted(all_packages[name]['versions'], reverse=True)
            )
            all_packages[name]['latest_version'] = versions[0]

        all_apps = {}
        for name in all_packages:
            versions = sort_versions(list(all_packages[name]['versions']))
            all_packages[name]['versions'] = versions[:]

            for version in versions:
                has_type = all_packages[name].get('type')
                # Has type in this case implies being an app
                if has_type:
                    all_apps[name] = all_packages[name].copy()
                    # Remove all versions that are not apps!
                    versions = all_apps[name]['versions'][:]
                    types = all_apps[name]['type']
                    app_versions = [v for v in versions if v in types]
                    all_apps[name]['versions'] = app_versions

        return all_packages, all_apps

    @staticmethod
    def _prepare_model_data(packages, linked, pip=None):
        """Prepare model data for the packages table model."""
        pip = pip if pip else []
        data = []
        linked_packages = {}
        for canonical_name in linked:
            name, version, b = tuple(canonical_name.rsplit('-', 2))
            linked_packages[name] = {'version': version}

        pip_packages = {}
        for canonical_name in pip:
            name, version, b = tuple(canonical_name.rsplit('-', 2))
            pip_packages[name] = {'version': version}

        packages_names = sorted(
            list(
                set(
                    list(linked_packages.keys()) + list(pip_packages.keys()) +
                    list(packages.keys())
                ),
            )
        )

        for name in packages_names:
            p_data = packages.get(name)

            summary = p_data.get('summary', '') if p_data else ''
            url = p_data.get('home', '') if p_data else ''
            license_ = p_data.get('license', '') if p_data else ''
            versions = p_data.get('versions', '') if p_data else []
            version = p_data.get('latest_version', '') if p_data else ''

            if name in pip_packages:
                type_ = C.PIP_PACKAGE
                version = pip_packages[name].get('version', '')
                status = C.INSTALLED
            elif name in linked_packages:
                type_ = C.CONDA_PACKAGE
                version = linked_packages[name].get('version', '')
                status = C.INSTALLED

                if version in versions:
                    vers = versions
                    upgradable = not version == vers[-1] and len(vers) != 1
                    downgradable = not version == vers[0] and len(vers) != 1

                    if upgradable and downgradable:
                        status = C.MIXGRADABLE
                    elif upgradable:
                        status = C.UPGRADABLE
                    elif downgradable:
                        status = C.DOWNGRADABLE
            else:
                type_ = C.CONDA_PACKAGE
                status = C.NOT_INSTALLED

                if version == '' and len(versions) != 0:
                    version = versions[-1]

            row = {
                C.COL_ACTION: C.ACTION_NONE,
                C.COL_PACKAGE_TYPE: type_,
                C.COL_NAME: name,
                C.COL_DESCRIPTION: summary.capitalize(),
                C.COL_VERSION: version,
                C.COL_STATUS: status,
                C.COL_URL: url,
                C.COL_LICENSE: license_,
                C.COL_ACTION_VERSION: None,
            }

            data.append(row)
        return data

    def _get_user_licenses(self, products=None):
        """Get user trial/paid licenses from anaconda.org."""
        license_data = []
        try:
            res = self._anaconda_client_api.user_licenses()
            license_data = res.get('data', [])

            # This should be returning a dict or list not a json string!
            if is_text_string(license_data):
                license_data = json.loads(license_data)
        except Exception:
            time.sleep(0.3)

        return license_data

    # --- Public API
    # -------------------------------------------------------------------------
    def reload_binstar_client(self):
        """
        Recreate the binstar client with new updated values.

        Notes:
        ------
        The Client needs to be restarted because on domain change it will not
        validate the user since it will check against the old domain, which
        was used to create the original client.

        See: https://github.com/ContinuumIO/navigator/issues/1325
        """
        config = binstar_client.utils.get_config()
        token = self.load_token()
        binstar = binstar_client.utils.get_server_api(
            token=token,
            site=None,
            cls=None,
            config=config,
            log_level=logging.NOTSET
        )
        self._anaconda_client_api = binstar
        return binstar

    def token(self):
        """Return the current token registered with authenticate."""
        return self._anaconda_client_api.token

    def load_token(self):
        """Load current authenticated token."""
        token = None
        try:
            token = binstar_client.utils.load_token(self.get_api_url())
        except Exception:
            pass
        return token

    def _login(self, username, password, application, application_url):
        """Login callback."""
        new_token = self._anaconda_client_api.authenticate(
            username, password, application, application_url
        )
        args = Args()
        args.site = None
        args.token = new_token
        binstar_client.utils.store_token(new_token, args)
        return new_token

    def login(self, username, password, application, application_url):
        """Login to anaconda server."""
        logger.debug(str((username, application, application_url)))
        method = self._login
        return self._create_worker(
            method, username, password, application, application_url
        )

    def logout(self):
        """
        Logout from anaconda.org.

        This method removes the authentication and removes the token.
        """
        error = None
        args = Args()
        args.site = None
        args.token = self.token

        binstar_client.utils.remove_token(args)
        if self.token:
            try:
                self._anaconda_client_api.remove_authentication()
            except binstar_client.errors.Unauthorized as e:
                error = e
                logger.debug(
                    "The token that you are trying to remove may "
                    "not be valid {}".format(e)
                )
            except Exception as e:
                error = e
                logger.debug("The certificate might be invalid. {}".format(e))

        logger.info("logout successful")
        return error

    def load_repodata(self, repodata, metadata=None, python_version=None):
        """
        Load all the available packages information for downloaded repodata.

        For downloaded repodata files (repo.anaconda.com), additional
        data provided (anaconda cloud), and additional metadata and merge into
        a single set of packages and apps.

        If python_version is not none, exclude all package/versions which
        require an incompatible version of python.

        Parameters
        ----------
        repodata: dict of dicts
            Data loaded from the conda cache directories.
        metadata: dict
            Metadata info form different sources. For now only from
            repo.anaconda.com
        python_version: str
            Python version used in preprocessing.
        """
        logger.debug('')
        method = self._load_repodata
        return self._create_worker(
            method,
            repodata,
            metadata=metadata,
            python_version=python_version,
        )

    def prepare_model_data(self, packages, linked, pip=None):
        """Prepare downloaded package info along with pip pacakges info."""
        logger.debug('')
        method = self._prepare_model_data
        return self._create_worker(
            method,
            packages,
            linked,
            pip=pip,
        )

    def set_domain(self, domain='https://api.anaconda.org'):
        """Reset current api domain."""
        logger.debug('Setting domain {}'.format(domain))
        config = binstar_client.utils.get_config()
        config['url'] = domain

        try:
            binstar_client.utils.set_config(config)
        except binstar_client.errors.BinstarError:
            logger.error('Could not write anaconda client configuation')
            traceback = format_exc()
            msg_box = MessageBoxError(
                title='Anaconda Client configuration error',
                text='Anaconda Client domain could not be updated.<br><br>'
                'This may result in Navigator not working properly.<br>',
                error='<pre>' + traceback + '</pre>',
                report=False,
                learn_more=None,
            )
            msg_box.exec_()

        self._anaconda_client_api = binstar_client.utils.get_server_api(
            token=None,
            log_level=logging.NOTSET,
        )

    def user(self):
        """Return current logged user information."""
        return self.organizations(login=None)

    def domain(self):
        """Return current domain."""
        return self._anaconda_client_api.domain

    def packages(
        self,
        login=None,
        platform=None,
        package_type=None,
        type_=None,
        access=None
    ):
        """Return all the available packages for a given user.

        Parameters
        ----------
        type_: Optional[str]
            Only find packages that have this conda `type`, (i.e. 'app').
        access : Optional[str]
            Only find packages that have this access level (e.g. 'private',
            'authenticated', 'public').
        """
        logger.debug('')
        method = self._anaconda_client_api.user_packages
        return self._create_worker(
            method,
            login=login,
            platform=platform,
            package_type=package_type,
            type_=type_,
            access=access,
        )

    def organizations(self, login):
        """List all the organizations a user has access to."""
        try:
            user = self._anaconda_client_api.user(login=login)
        except Exception:
            user = {}
        return user

    @staticmethod
    def get_api_url():
        """Get the anaconda client url configuration."""
        config_data = binstar_client.utils.get_config()
        return config_data.get('url', 'https://api.anaconda.org')

    @staticmethod
    def set_api_url(url):
        """Set the anaconda client url configuration."""
        config_data = binstar_client.utils.get_config()
        config_data['url'] = url
        try:
            binstar_client.utils.set_config(config_data)
        except Exception as e:
            logger.error('Could not write anaconda client configuration')
            msg_box = MessageBoxError(
                title='Anaconda Client configuration error',
                text='Anaconda Client configuration could not be updated.<br>'
                'This may result in Navigator not working properly.<br>',
                error=e,
                report=False,
                learn_more=None,
            )
            msg_box.exec_()

    def get_ssl(self, set_conda_ssl=True):
        """
        Get the anaconda client url configuration and set conda accordingly.
        """
        config = binstar_client.utils.get_config()
        value = config.get('ssl_verify', config.get('verify_ssl', True))
        # ssl_verify = self._conda_api.config_get('ssl_verify').communicate()
        # if ssl_verify != value:   # FIXME: Conda rstricted acces to the key
        #     self._conda_api.config_set('ssl_verify', value).communicate()
        if set_conda_ssl:
            self._conda_api.config_set('ssl_verify', value).communicate()

        return value

    def set_ssl(self, value):
        """Set the anaconda client url configuration."""
        config_data = binstar_client.utils.get_config()
        config_data['verify_ssl'] = value
        config_data['ssl_verify'] = value
        try:
            binstar_client.utils.set_config(config_data)
            self._conda_api.config_set('ssl_verify', value).communicate()
        except Exception as e:
            logger.error('Could not write anaconda client configuration')
            msg_box = MessageBoxError(
                title='Anaconda Client configuration error',
                text='Anaconda Client configuration could not be updated.<br>'
                'This may result in Navigator not working properly.<br>',
                error=e,
                report=False,
                learn_more=None,
            )
            msg_box.exec_()

    def get_user_licenses(self, products=None):
        """Get user trial/paid licenses from anaconda.org."""
        logger.debug(str((products)))
        method = self._get_user_licenses
        return self._create_worker(method, products=products)

    def _get_api_info(self, url, proxy_servers=None, verify=True):
        """Callback."""
        proxy_servers = proxy_servers or {}
        data = {
            "api_url": url,
            "api_docs_url": "https://api.anaconda.org/docs",
            "brand": DEFAULT_BRAND,
            "conda_url": "https://conda.anaconda.org",
            "main_url": "https://anaconda.org",
            "pypi_url": "https://pypi.anaconda.org",
            "swagger_url": "https://api.anaconda.org/swagger.json",
        }
        if self._is_internet_available():
            try:
                r = requests.get(
                    url,
                    proxies=proxy_servers,
                    verify=verify,
                    timeout=self.DEFAULT_TIMEOUT,
                )
                content = to_text_string(r.content, encoding='utf-8')
                new_data = json.loads(content)

                # Enforce no trailing slash
                for key, value in new_data.items():
                    if is_text_string(value):
                        data[key] = value[:-1] if value[-1] == '/' else value

            except Exception as error:
                logger.error(str(error))

        return data

    def get_api_info(self, url, proxy_servers=None, verify=True):
        """Query anaconda api info."""
        logger.debug(str((url)))
        proxy_servers = proxy_servers or {}
        method = self._get_api_info
        return self._create_worker(
            method, url, proxy_servers=proxy_servers, verify=verify
        )


def is_dependency_met(deplist, version, package='python', debug=False):
    """Can this package dependency list be met given the pinned version."""
    flag = True
    try:
        s = re.compile("([^ ><=]+)([ <>=]+)([\d.*]+)")
        for dep in deplist:
            pname, rel, vers = s.match(dep).groups()
            rel = rel.replace(' ', '')

            if pname != package:
                continue

            if debug:
                print([pname, rel, vers])

            if "*" in vers:
                flag = bool(re.match(vers.replace("*", ".*"), version))
            elif not rel or rel == "==":
                flag = vers == version
                break
            elif rel == '<':
                flag = version.split('.') < vers.split('.')
            elif rel == '>':
                flag = version.split('.') > vers.split('.')
            elif rel == '<=':
                flag = version.split('.') <= vers.split('.')
            elif rel == '>=':
                flag = version.split('.') >= vers.split('.')
            elif rel == '!=':
                flag = version.split('.') != vers.split('.')
            else:
                continue
            break
    finally:
        return flag


CLIENT_API = None


def ClientAPI(config=None):
    """Client API threaded worker."""
    global CLIENT_API

    if CLIENT_API is None:
        CLIENT_API = _ClientAPI(config=config)

    return CLIENT_API


def print_output(worker, output, error):  # pragma: no cover
    """Test helper print function."""
    print(output, error)


def local_test():  # pragma: no cover
    """Local main test."""
    from anaconda_navigator.utils.qthelpers import qapplication

    app = qapplication()
    api = ClientAPI()
    api.login('goanpeca', 'asdasd', 'baby', '')
    api.login('bruce', 'asdasd', 'baby', '')
    # api.set_domain(domain='https://api.anaconda.org')
    # worker = api.multi_packages(logins=['goanpeca', 'binstar'])
    # worker.sig_finished.connect(print_output)
    # worker = api.organizations(login='goanpeca')
    # print(api.get_api_url())
    app.exec_()


if __name__ == '__main__':  # pragma: no cover
    local_test()
