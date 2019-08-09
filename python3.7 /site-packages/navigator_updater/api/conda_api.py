# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""
Updated `conda-api` running on a Qt QProcess to avoid UI blocking.

This also add some extra methods to the original conda-api.
"""

# yapf: disable

# Standard library imports
from collections import deque
from os.path import abspath, basename, expanduser, isdir, join
import hashlib
import json
import os
import platform
import re
import sys

# Third party imports
from qtpy.QtCore import QByteArray, QObject, QProcess, QTimer, Signal
import yaml

# Local imports
from navigator_updater.config import WIN, get_home_dir
from navigator_updater.utils.conda import get_conda_info
from navigator_updater.utils.encoding import ensure_binary
from navigator_updater.utils.findpip import PIP_LIST_SCRIPT
from navigator_updater.utils.logs import logger
from navigator_updater.utils.misc import path_is_writable

# yapf: enable

__version__ = '1.3.0'

if WIN:
    import ctypes

# --- Constants
# -----------------------------------------------------------------------------
CONDA_API = None


# --- Errors
# -----------------------------------------------------------------------------
class PipError(Exception):
    """General pip error."""

    pass


class CondaError(Exception):
    """General Conda error."""

    pass


class CondaProcessWorker(CondaError):
    """General Conda error."""

    pass


class CondaEnvExistsError(CondaError):
    """Conda environment already exists."""

    pass


# --- Helpers
# -----------------------------------------------------------------------------
PY2 = sys.version[0] == '2'
PY3 = sys.version[0] == '3'
DEBUG = False


def to_text_string(obj, encoding=None):
    """Convert `obj` to (unicode) text string."""
    if PY2:
        # Python 2
        if encoding is None:
            return unicode(obj)  # NOQA
        else:
            return unicode(obj, encoding)  # NOQA
    else:
        # Python 3
        if encoding is None:
            return str(obj)
        elif isinstance(obj, str):
            # In case this function is not used properly, this could happen
            return obj
        else:
            return str(obj, encoding)


def handle_qbytearray(obj, encoding):
    """Qt/Python3 compatibility helper."""
    if isinstance(obj, QByteArray):
        obj = obj.data()

    return to_text_string(obj, encoding=encoding)


class ProcessWorker(QObject):
    """Conda worker based on a QProcess for non blocking UI."""

    sig_chain_finished = Signal(object, object, object)
    sig_finished = Signal(object, object, object)
    sig_partial = Signal(object, object, object)

    def __init__(
        self,
        cmd_list,
        parse=False,
        pip=False,
        callback=None,
        extra_kwargs=None,
        environ=None
    ):
        """Conda worker based on a QProcess for non blocking UI.

        Parameters
        ----------
        cmd_list : list of str
            Command line arguments to execute.
        parse : bool (optional)
            Parse json from output.
        pip : bool (optional)
            Define as a pip command.
        callback : func (optional)
            If the process has a callback to process output from comd_list.
        extra_kwargs : dict
            Arguments for the callback.
        """
        super(ProcessWorker, self).__init__()
        self._result = None
        self._cmd_list = cmd_list
        self._parse = parse
        self._pip = pip
        self._conda = not pip
        self._callback = callback
        self._fired = False
        self._communicate_first = False
        self._partial_stdout = None
        self._extra_kwargs = extra_kwargs if extra_kwargs else {}

        self._timer = QTimer()
        self._process = QProcess()
        self._set_environment(environ)

        self._timer.setInterval(150)

        self._timer.timeout.connect(self._communicate)
        # self._process.finished.connect(self._communicate)
        self._process.readyReadStandardOutput.connect(self._partial)

    def get_encoding(self):
        """Return the encoding/codepage to use."""
        enco = 'utf-8'
        #  Currently only cp1252 is allowed
        if WIN:
            codepage = str(ctypes.cdll.kernel32.GetACP())
            # import locale
            # locale.getpreferredencoding()  # Differences?
            enco = 'cp' + codepage
        return enco

    def _set_environment(self, environ):
        """Set the environment on the QProcess."""
        if environ:
            q_environ = self._process.processEnvironment()
            for k, v in environ.items():
                q_environ.insert(k, v)
            self._process.setProcessEnvironment(q_environ)

    def _partial(self):
        """Callback for partial output."""
        # if self._process != QProcess.NotRunning:
        raw_stdout = self._process.readAllStandardOutput()
        stdout = handle_qbytearray(raw_stdout, self.get_encoding())

        try:
            json_stdout = [json.loads(s) for s in stdout.split('\x00') if s]
            json_stdout = json_stdout[-1]
        except Exception:
            json_stdout = stdout

        if self._partial_stdout is None:
            self._partial_stdout = stdout
        else:
            self._partial_stdout += stdout

        self.sig_partial.emit(self, json_stdout, None)

    def _communicate(self):
        """Callback for communicate."""
        if (not self._communicate_first and
                self._process.state() == QProcess.NotRunning):
            self.communicate()
        elif self._fired:
            self._timer.stop()

    def communicate(self):
        """Retrieve information."""
        self._communicate_first = True
        self._process.waitForFinished()

        enco = self.get_encoding()
        if self._partial_stdout is None:
            raw_stdout = self._process.readAllStandardOutput()
            stdout = handle_qbytearray(raw_stdout, enco)
        else:
            stdout = self._partial_stdout

        raw_stderr = self._process.readAllStandardError()
        stderr = handle_qbytearray(raw_stderr, enco)
        result = [stdout.encode(enco), stderr.encode(enco)]

        # FIXME: Why does anaconda client print to stderr???
        if PY2:
            stderr = stderr.decode()

        if 'using anaconda' not in stderr.lower():
            if stderr.strip() and self._conda:
                d = {'command': ' '.join(self._cmd_list), 'stderr': stderr}
                # These messages should be harmless, but we still display
                # them in debugging scenarios for feedback. Used to be
                # warnings, but this was confusing users
                logger.debug('Conda command output on stderr {0}'.format(d))
            elif stderr.strip() and self._pip:
                d = {'command': ' '.join(self._cmd_list)}
                # Same as above
                logger.debug('Pip command output on stderr', extra=d)
        result[-1] = ''

        if self._parse and stdout:
            json_stdout = []
            json_lines_output = stdout.split('\x00')
            for i, l in enumerate(json_lines_output):
                if l:
                    try:
                        json_stdout.append(json.loads(l))
                    except Exception as error:
                        # An exception here could be product of:
                        # - conda env installing pip stuff that is thrown to
                        #   stdout in non json form
                        # - a post link script might be printing stuff to
                        #   stdout in non json format
                        logger.warning(
                            (
                                'Problem parsing conda json output. '
                                'Line {0}. Data - {1}. Error - {2}'.format(
                                    i, l, str(error)
                                )
                            ),
                        )

            if json_stdout:
                json_stdout = json_stdout[-1]
            result = json_stdout, result[-1]

            out = result[0]
            if 'exception_name' in out or 'exception_type' in out:
                if not isinstance(out, dict):
                    result = {'error': str(out)}, None
                else:
                    error = '{0}: {1}'.format(
                        " ".join(self._cmd_list), out.get('message', '')
                    )
                    result = out, error

        if self._callback:
            result = self._callback(result[0], stderr,
                                    **self._extra_kwargs), result[-1]

        self._result = result

        # Handle special case where no --json flag exists
        #        if isinstance(result[0], bytes):
        #            result[0] = {}

        # TODO: Remove chained signals and use a _sig_finished
        self.sig_finished.emit(self, result[0], result[-1])

        if result[-1]:
            d = {'stderr': result[-1]}
            logger.debug('error', extra=d)

        self._fired = True

        return result

    def close(self):
        """Close the running process."""
        self._process.close()

    def is_finished(self):
        """Return True if worker has finished processing."""
        return self._process.state() == QProcess.NotRunning and self._fired

    def start(self):
        """Start process."""
        logger.debug(str(' '.join(self._cmd_list)))

        if not self._fired:
            self._partial_ouput = None
            #            print(os.environ)
            #            print(self._process.processEnvironment().keys())
            self._process.start(self._cmd_list[0], self._cmd_list[1:])
            self._timer.start()
        else:
            raise CondaProcessWorker(
                'A Conda ProcessWorker can only run once '
                'per method call.'
            )


# --- API
# -----------------------------------------------------------------------------
class _CondaAPI(QObject):
    """Conda API to connect to conda in a non blocking way via QProcess."""

    def __init__(self, parent=None):
        """Conda API to connect to conda in a non blocking way via QProcess."""
        super(_CondaAPI, self).__init__()

        # Variables
        self._parent = parent
        self._queue = deque()
        self._timer = QTimer()
        self._current_worker = None
        self._workers = []

        # Conda config values
        self.CONDA_PREFIX = None
        self.ROOT_PREFIX = None
        self._envs_dirs = None
        self._pkgs_dirs = None
        self._user_agent = None
        self._proxy_servers = None
        self._conda_version = None

        self.set_conda_prefix(info=get_conda_info())

        self.user_rc_path = abspath(expanduser('~/.condarc'))
        self.sys_rc_path = join(self.ROOT_PREFIX, '.condarc')

        # Setup
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._clean)

    def _clean(self):
        """Remove references of inactive workers periodically."""
        if self._workers:
            for w in self._workers:
                if w.is_finished():
                    self._workers.remove(w)
        else:
            self._current_worker = None
            self._timer.stop()

    def _start(self):
        if len(self._queue) == 1:
            self._current_worker = self._queue.popleft()
            self._workers.append(self._current_worker)
            self._current_worker.start()
            self._timer.start()

    def is_active(self):
        """Check if a worker is still active."""
        return len(self._workers) == 0

    def terminate_all_processes(self):
        """Kill all working processes."""
        for worker in self._workers:
            # Try to disconnect signals first
            try:
                worker.sig_finished.disconnect()
            except Exception:
                pass
            try:
                worker.sig_partial.disconnect()
            except Exception:
                pass
            # Now close the worker
            worker.close()

    # --- Conda api
    # -------------------------------------------------------------------------
    def _call_conda(
        self,
        extra_args,
        abspath=True,
        parse=False,
        callback=None,
        environ=None
    ):
        """
        Call conda with the list of extra arguments, and return the worker.

        The result can be force by calling worker.communicate(), which returns
        the tuple (stdout, stderr).
        """
        if abspath:
            if sys.platform == 'win32':
                python = join(self.ROOT_PREFIX, 'python.exe')
                conda = join(self.ROOT_PREFIX, 'Scripts', 'conda-script.py')
            else:
                python = join(self.ROOT_PREFIX, 'bin/python')
                conda = join(self.ROOT_PREFIX, 'bin/conda')
            cmd_list = [python, conda]
        else:
            # Just use whatever conda is on the path
            cmd_list = ['conda']

        cmd_list.extend(extra_args)

        process_worker = ProcessWorker(
            cmd_list,
            parse=parse,
            callback=callback,
            environ=environ,
        )
        process_worker.sig_finished.connect(self._start)
        self._queue.append(process_worker)
        self._start()

        return process_worker

    def _call_and_parse(
        self, extra_args, abspath=True, callback=None, environ=None
    ):
        return self._call_conda(
            extra_args,
            abspath=abspath,
            parse=True,
            callback=callback,
            environ=environ,
        )

    @staticmethod
    def _setup_install_commands_from_kwargs(kwargs, keys=tuple()):
        """Setup install commands for conda."""
        cmd_list = []
        if kwargs.get('override_channels', False) and 'channel' not in kwargs:
            raise TypeError('conda search: override_channels requires channel')

        if 'env' in kwargs:
            cmd_list.extend(['--name', kwargs.pop('env')])
        if 'prefix' in kwargs:
            cmd_list.extend(['--prefix', kwargs.pop('prefix')])
        if 'channel' in kwargs:
            channel = kwargs.pop('channel')
            if isinstance(channel, str):
                cmd_list.extend(['--channel', channel])
            else:
                cmd_list.append('--channel')
                cmd_list.extend(channel)

        for key in keys:
            if key in kwargs and kwargs[key]:
                cmd_list.append('--' + key.replace('_', '-'))

        return cmd_list

    def _set_environment_variables(self, prefix=None, no_default_python=False):
        """Set the right CONDA_PREFIX environment variable."""
        environ_copy = os.environ.copy()
        conda_prefix = self.ROOT_PREFIX
        if prefix:
            conda_prefix = prefix

        if conda_prefix:
            if conda_prefix == self.ROOT_PREFIX:
                name = 'root'
            else:
                name = os.path.basename(conda_prefix)
            environ_copy['CONDA_PREFIX'] = conda_prefix
            environ_copy['CONDA_DEFAULT_ENV'] = name

        if no_default_python:
            environ_copy['CONDA_DEFAULT_PYTHON'] = None

        return environ_copy

    def set_conda_prefix(self, info=None):
        """
        Set the prefix of the conda environment.

        This function should only be called once (right after importing
        conda_api).
        """
        if info is None:
            # Find some conda instance, and then use info to get 'root_prefix'
            worker = self.info(abspath=False)
            info = worker.communicate()[0]
        else:
            self.ROOT_PREFIX = info['root_prefix']
            self.CONDA_PREFIX = info['conda_prefix']
            self._envs_dirs = info['envs_dirs']
            self._pkgs_dirs = info['pkgs_dirs']
            self._user_agent = info['user_agent']

            version = []
            for part in info['conda_version'].split('.'):
                try:
                    new_part = int(part)
                except ValueError:
                    new_part = part

                version.append(new_part)

            self._conda_version = tuple(version)

    def get_conda_version(self):
        """Return the version of conda being used (invoked) as a string."""
        return self._call_conda(
            ['--version'],
            callback=self._get_conda_version,
        )

    @staticmethod
    def _get_conda_version(stdout, stderr):
        """Callback for get_conda_version."""
        # argparse outputs version to stderr in Python < 3.4.
        # http://bugs.python.org/issue18920
        pat = re.compile(r'conda:?\s+(\d+\.\d\S+|unknown)')
        try:
            m = pat.match(stderr.decode().strip())
        except Exception:
            m = pat.match(stderr.strip())

        if m is None:
            try:
                m = pat.match(stdout.decode().strip())
            except Exception:
                m = pat.match(stdout.strip())

        if m is None:
            raise Exception('output did not match: {0}'.format(stderr))

        return m.group(1)

    @property
    def pkgs_dirs(self):
        """Conda package cache directories."""
        if self._pkgs_dirs:
            pkgs = self._pkgs_dirs
        else:
            # Legacy behavior
            pkgs_path = os.sep.join([self.ROOT_PREFIX, 'pkgs'])
            user_pkgs_path = os.sep.join([get_home_dir(), '.conda', 'pkgs'])
            pkgs = pkgs_path + user_pkgs_path

        return pkgs

    @property
    def envs_dirs(self):
        """
        Conda environment directories.

        The first writable item should be used.
        """
        if self._envs_dirs:
            envs_dirs = self._envs_dirs
        else:
            # Legacy behavior
            envs_path = os.sep.join([self.ROOT_PREFIX, 'envs'])
            user_envs_path = os.sep.join([get_home_dir(), '.conda', 'envs'])
            envs_dirs = [envs_path, user_envs_path]

        return envs_dirs

    @property
    def user_agent(self):
        return self._user_agent

    @property
    def envs_dirs_writable(self):
        """Conda writable environment directories."""
        writable = []
        for env_dir in self.envs_dirs:
            if path_is_writable(env_dir):
                writable.append(env_dir)
        return writable

    def get_envs(self, log=True):
        """Return environment list of absolute path to their prefixes."""
        if log:
            logger.debug('')

        all_envs = []
        for env in self.envs_dirs:
            if os.path.isdir(env):
                envs_names = os.listdir(env)
                all_envs += [os.sep.join([env, i]) for i in envs_names]

        valid_envs = [
            env for env in all_envs
            if os.path.isdir(env) and self.environment_exists(prefix=env)
        ]

        return valid_envs

    def get_prefix_envname(self, name, log=None):
        """Return full prefix path of environment defined by `name`."""
        prefix = None
        if name == 'root':
            prefix = self.ROOT_PREFIX

        envs = self.get_envs()
        for p in envs:
            if basename(p) == name:
                prefix = p

        return prefix

    def get_name_envprefix(self, prefix):
        """
        Return name of environment defined by full `prefix` path.

        Returns the name if it is located in the default conda environments
        directory, otherwise it returns the prefix.
        """
        name = os.path.basename(prefix)
        if not (name and self.environment_exists(name=name)):
            name = prefix
        return name

    @staticmethod
    def linked(prefix, apps=False):
        """Return set of canonical names of linked packages in `prefix`."""
        logger.debug(str(prefix))

        if not os.path.isdir(prefix):
            return set()

        packages = set()
        meta_dir = join(prefix, 'conda-meta')

        if isdir(meta_dir):
            meta_files = set(
                fname for fname in os.listdir(meta_dir)
                if fname.endswith('.json')
            )
            if apps:
                for fname in meta_files:
                    fpath = os.path.join(meta_dir, fname)

                    if os.path.isfile(fpath):
                        with open(fpath) as f:
                            data = f.read()

                        if 'app_entry' in data or 'app_type' in data:
                            packages.add(fname[:-5])
            else:
                packages = set(fname[:-5] for fname in meta_files)

        return packages

    def linked_apps_info(self, prefix):
        """Return local installed apps info on prefix."""
        linked_apps = self.linked(prefix, apps=True)
        meta_dir = join(prefix, 'conda-meta')

        apps_info = {}
        for linked_app in linked_apps:
            fpath = os.path.join(meta_dir, linked_app + '.json')
            if os.path.isfile(fpath):
                with open(fpath) as f:
                    data = json.load(f)

                n, v, b = self.split_canonical_name(linked_app)
                app_info = {
                    'name': data.get('name', n),
                    'description': data.get('summary', ''),
                    'versions': [v],
                    'command': data.get('app_entry', ''),
                    'app_entry': {
                        v: data.get('app_entry', '')
                    },
                    'image_path': None,
                }
                apps_info[n] = app_info

        return apps_info

    @staticmethod
    def split_canonical_name(cname):
        """Split a canonical package name into name, version, build."""
        return tuple(cname.rsplit('-', 2))

    def info(self, prefix=None, abspath=True):
        """Return a dictionary with configuration information."""
        logger.debug(str(''))
        environ = self._set_environment_variables(prefix)
        return self._call_and_parse(
            ['info', '--json'],
            abspath=abspath,
            environ=environ,
        )

    def package_info(self, package, abspath=True):
        """Return a dictionary with package information."""
        return self._call_and_parse(
            ['info', package, '--json'],
            abspath=abspath,
        )

    def search(self, regex=None, spec=None, prefix=None, **kwargs):
        """Search for packages."""
        cmd_list = ['search', '--json']
        environ = self._set_environment_variables(prefix)

        if regex and spec:
            raise TypeError('conda search: only one of regex or spec allowed')

        if regex:
            cmd_list.append(regex)

        if spec:
            cmd_list.extend(['--spec', spec])

        if 'platform' in kwargs:
            cmd_list.extend(['--platform', kwargs.pop('platform')])

        cmd_list.extend(
            self._setup_install_commands_from_kwargs(
                kwargs, (
                    'canonical',
                    'unknown',
                    'use_index_cache',
                    'outdated',
                    'override_channels',
                )
            )
        )

        return self._call_and_parse(
            cmd_list,
            abspath=kwargs.get('abspath', True),
            environ=environ,
        )

    def parse_token_channel(self, channel, token):
        """
        Adapt a channel to include token of the logged user.

        Ignore default channels, and ignore channels that already include a
        token.
        """
        if (token and channel not in self.DEFAULT_CHANNELS and
                channel != 'defaults' and '/t/' not in channel):
            url_parts = channel.split('/')
            start = url_parts[:-1]
            middle = 't/{0}'.format(token)
            end = url_parts[-1]
            token_channel = '{0}/{1}/{2}'.format('/'.join(start), middle, end)
            return token_channel
        else:
            return channel

    # --- Conda Environment Actions
    # -------------------------------------------------------------------------
    def _create_from_yaml(self, yamlfile, prefix=None, name=None):
        """
        Create new environment using conda-env via a yaml specification file.

        Unlike other methods, this calls conda-env, and requires a named
        environment and uses channels as defined in rcfiles.

        Parameters
        ----------
        name : string
            Environment name
        yamlfile : string
            Path to yaml file with package spec (as created by conda env export
        """
        logger.debug(str((name, yamlfile)))
        if name is None and prefix is None:
            raise TypeError('must specify a `name` or `prefix`')

        cmd_list = ['env', 'create', '-f', yamlfile, '--json']
        if name:
            cmd_list.extend(['--name', name])
        elif prefix:
            cmd_list.extend(['--prefix', prefix])

        return self._call_and_parse(cmd_list)

    def create(
        self,
        name=None,
        prefix=None,
        pkgs=None,
        file=None,
        no_default_python=False
    ):
        """
        Create an environment with a specified set of packages.

        Default python option is on deprecation route for 4.4.
        """
        logger.debug(str((prefix, pkgs)))

        environ = self._set_environment_variables(
            prefix=prefix, no_default_python=no_default_python
        )

        if name is None and prefix is None:
            raise TypeError('must specify a `name` or `prefix`')

        if file and file.endswith(('.yaml', 'yml')):
            result = self._create_from_yaml(file, prefix=prefix, name=name)
        else:
            if not pkgs or not isinstance(pkgs, (list, tuple)):
                raise TypeError(
                    'must specify a list of one or more packages to '
                    'install into new environment'
                )

            # mkdir removed in conda 4.6
            if self._conda_version > (4, 5):
                cmd_list = ['create', '--yes', '--json']
            else:
                cmd_list = ['create', '--yes', '--json', '--mkdir']

            if name:
                ref = name
                search = [os.path.join(d, name) for d in self.envs_dirs]
                cmd_list.extend(['--name', name])
            elif prefix:
                ref = prefix
                search = [prefix]
                cmd_list.extend(['--prefix', prefix])
            else:
                raise TypeError(
                    'must specify either an environment name or a '
                    'path for new environment'
                )

            if any(os.path.exists(prefix) for prefix in search):
                raise CondaEnvExistsError(
                    'Conda environment {0} already '
                    'exists'.format(ref)
                )

            cmd_list.extend(pkgs)
            result = self._call_and_parse(cmd_list, environ=environ)

        return result

    def install(
        self,
        name=None,
        prefix=None,
        pkgs=None,
        dep=True,
        dry_run=False,
        no_default_python=False
    ):
        """Install a set of packages into an environment by name or path."""
        logger.debug(str((prefix, pkgs)))

        environ = self._set_environment_variables(
            prefix=prefix, no_default_python=no_default_python
        )

        # TODO: Fix temporal hack
        if not pkgs or not isinstance(pkgs, (list, tuple, str)):
            raise TypeError(
                'must specify a list of one or more packages to '
                'install into existing environment'
            )

        cmd_list = ['install', '--yes', '--json', '--force-pscheck']
        if name:
            cmd_list.extend(['--name', name])
        elif prefix:
            cmd_list.extend(['--prefix', prefix])
        else:
            # Just install into the current environment, whatever that is
            pass

        # TODO: Fix temporal hack
        if isinstance(pkgs, (list, tuple)):
            cmd_list.extend(pkgs)
        elif isinstance(pkgs, str):
            cmd_list.extend(['--file', pkgs])

        if not dep:
            cmd_list.extend(['--no-deps'])

        if dry_run:
            cmd_list.extend(['--dry-run'])

        return self._call_and_parse(cmd_list, environ=environ)

    def update(
        self,
        name=None,
        prefix=None,
        pkgs=None,
        dep=True,
        all_=False,
        dry_run=False,
        no_default_python=False,
    ):
        """Install a set of packages into an environment by name or path."""
        logger.debug(str((prefix, pkgs)))

        environ = self._set_environment_variables(
            prefix=prefix, no_default_python=no_default_python
        )

        cmd_list = ['update', '--yes', '--json', '--force-pscheck']
        if not pkgs and not all_:
            raise TypeError(
                "Must specify at least one package to update, or "
                "all_=True."
            )

        if name:
            cmd_list.extend(['--name', name])
        elif prefix:
            cmd_list.extend(['--prefix', prefix])
        else:
            # Just install into the current environment, whatever that is
            pass

        if isinstance(pkgs, (list, tuple)):
            cmd_list.extend(pkgs)

        if not dep:
            cmd_list.extend(['--no-deps'])

        if dry_run:
            cmd_list.extend(['--dry-run'])

        return self._call_and_parse(cmd_list, environ=environ)

    def remove(
        self, name=None, prefix=None, pkgs=None, all_=False, dry_run=False
    ):
        """
        Remove a package (from an environment) by name.

        Returns {
            success: bool, (this is always true),
            (other information)
        }
        """
        logger.debug(str((prefix, pkgs)))

        cmd_list = ['remove', '--json', '--yes']

        if not pkgs and not all_:
            raise TypeError(
                "Must specify at least one package to remove, or "
                "all=True."
            )

        if name:
            cmd_list.extend(['--name', name])
        elif prefix:
            cmd_list.extend(['--prefix', prefix])
        else:
            raise TypeError(
                'must specify either an environment name or a '
                'path for package removal'
            )

        if all_:
            cmd_list.extend(['--all'])
        else:
            cmd_list.extend(pkgs)

        if dry_run:
            cmd_list.extend(['--dry-run'])

        return self._call_and_parse(cmd_list)

    def remove_environment(self, name=None, prefix=None):
        """Remove an environment entirely specified by `name` or `prefix`."""
        return self.remove(name=name, prefix=prefix, all_=True)

    def clone_environment(
        self, clone_from_prefix, name=None, prefix=None, **kwargs
    ):
        """Clone the environment `clone` into `name` or `prefix`."""
        cmd_list = ['create', '--json']

        if (name and prefix) or not (name or prefix):
            raise TypeError(
                "conda clone_environment: exactly one of `name` "
                "or `path` required"
            )

        if name:
            cmd_list.extend(['--name', name])

        if prefix:
            cmd_list.extend(['--prefix', prefix])

        cmd_list.extend(['--clone', clone_from_prefix])

        cmd_list.extend(
            self._setup_install_commands_from_kwargs(
                kwargs, (
                    'dry_run',
                    'unknown',
                    'use_index_cache',
                    'use_local',
                    'no_pin',
                    'force',
                    'all',
                    'channel',
                    'override_channels',
                    'no_default_packages',
                )
            )
        )
        return self._call_and_parse(
            cmd_list,
            abspath=kwargs.get('abspath', True),
        )

    # --- Conda Configuration
    # -------------------------------------------------------------------------
    @staticmethod
    def _setup_config_from_kwargs(kwargs):
        """Setup config commands for conda."""
        cmd_list = ['--json', '--force']

        if 'file' in kwargs:
            cmd_list.extend(['--file', kwargs['file']])

        if 'system' in kwargs:
            cmd_list.append('--system')

        return cmd_list

    def _setup_config_args(self, file=None, prefix=None, system=False):
        """Setup config commands for conda."""
        cmd_list = ['--json', '--force']

        if file:
            config_file = file
        elif prefix and self.environment_exists(prefix):
            config_file = os.path.join(self.ROOT_PREFIX, '.condarc')
        elif system:
            config_file = self.sys_rc_path
        else:
            config_file = self.user_rc_path

        cmd_list.extend(['--file', config_file])

        return cmd_list

    def config_get(self, *keys, **kwargs):
        """
        Get the values of configuration keys.

        Returns a dictionary of values. Note, the key may not be in the
        dictionary if the key wasn't set in the configuration file.
        """
        cmd_list = ['config', '--get']
        cmd_list.extend(keys)
        cmd_list.extend(self._setup_config_from_kwargs(kwargs))

        return self._call_and_parse(
            cmd_list,
            abspath=kwargs.get('abspath', True),
            callback=lambda o, e: o['get']
        )

    def config_set(
        self, key, value, file=None, prefix=None, system=False, abspath=True
    ):
        """
        Set a key to a (bool) value.

        Returns a list of warnings Conda may have emitted.
        """
        cmd_list = ['config', '--set', key, str(value)]
        args = self._setup_config_args(system=system, file=file, prefix=prefix)
        cmd_list.extend(args)

        return self._call_and_parse(
            cmd_list,
            abspath=abspath,
            callback=lambda o, e: o.get('warnings', [])
        )

    def config_append(
        self, key, value, file=None, prefix=None, system=False, abspath=True
    ):
        """
        Append entry to the end of a list key.

        Returns a list of warnings Conda may have emitted.
        """
        cmd_list = ['config', '--append', key, value]
        args = self._setup_config_args(system=system, file=file, prefix=prefix)
        cmd_list.extend(args)

        return self._call_and_parse(
            cmd_list,
            abspath=abspath,
            callback=lambda o, e: o.get('warnings', [])
        )

    def config_prepend(
        self, key, value, file=None, prefix=None, system=False, abspath=True
    ):
        """Prepend entry to the start of a list key."""
        return self.config_add(
            key,
            value,
            file=file,
            prefix=prefix,
            system=system,
            abspath=abspath
        )

    def config_add(
        self, key, value, file=None, prefix=None, system=False, abspath=True
    ):
        """
        Add a value to a key.

        Returns a list of warnings Conda may have emitted.
        """
        cmd_list = ['config', '--add', key, value]
        args = self._setup_config_args(system=system, file=file, prefix=prefix)
        cmd_list.extend(args)

        return self._call_and_parse(
            cmd_list,
            abspath=abspath,
            callback=lambda o, e: o.get('warnings', [])
        )

    def config_remove(
        self, key, value, file=None, prefix=None, system=False, abspath=True
    ):
        """
        Remove a value from a key.

        Returns a list of warnings Conda may have emitted.
        """
        cmd_list = ['config', '--remove', key, value]
        args = self._setup_config_args(system=system, file=file, prefix=prefix)
        cmd_list.extend(args)

        return self._call_and_parse(
            cmd_list,
            abspath=abspath,
            callback=lambda o, e: o.get('warnings', [])
        )

    def config_remove_key(
        self, key, file=None, prefix=None, system=False, abspath=True
    ):
        """"""
        return self.config_delete(
            key, file=file, prefix=prefix, system=system, abspath=abspath
        )

    def config_delete(
        self, key, file=None, prefix=None, system=False, abspath=True
    ):
        """
        Remove a key entirely.

        Returns a list of warnings Conda may have emitted.
        """
        cmd_list = ['config', '--remove-key', key]
        args = self._setup_config_args(system=system, file=file, prefix=prefix)
        cmd_list.extend(args)

        return self._call_and_parse(
            cmd_list,
            abspath=abspath,
            callback=lambda o, e: o.get('warnings', [])
        )

    @staticmethod
    def _config_show_sources(sources, error, prefix=None, all_=False):
        """Callback for show sources method."""
        if 'cmd_line' in sources:
            sources.pop('cmd_line')

            for k, v in sources.items():
                if not os.path.isfile(k):
                    sources.pop(k)

#            # Include additional sources based on keywords
#            envs_configs_paths = []
#            if all_:
#                envs_prefixes = self.get_envs()
#                for env_prefix in envs_prefixes:
#                    env_config_path = os.path.join(env_prefix, '.condarc')
#                    if env_config_path not in sources:
#                        config_data = self.load_rc(prefix=env_prefix)
#                        if config_data:
#                            sources[env_config_path] = config_data
#                            envs_configs_paths.append(env_config_path)
#            elif prefix:
#                env_config_path = os.path.join(prefix, '.condarc')
#                if os.path.isfile(env_config_path):
#                    sources[env_config_path] = self.load_rc(prefix=prefix)
#
#            # Sort the results based on precedence?
#            envs_configs_paths = sorted(envs_configs_paths)
#            ordered_paths = [self.sys_rc_path, self.user_rc_path]
#            ordered_paths.extend(envs_configs_paths)
#            extra_paths = [p for p in sources if p not in ordered_paths]
#            ordered_sources = OrderedDict()
#            for path in extra_paths + ordered_paths:
#                if path in sources:
#                    ordered_sources[path] = sources[path]

#        return ordered_sources
        return sources

    def config_show_sources(self, prefix=None, all_=False):
        """
        Show configuration sources.

        Parameters
        ----------
        prefix : str
            This is equivalent of using `--env` flag for the activated
            environent `prefix`.
        all : bool
            This includes all the configuration options in envs, which depend
            on the concept of an activated environment. If both prefix and
            all are provided, all overides the specific path.
        """
        return self.config_show(sources=True, prefix=prefix, all_=all_)

    def config_show(
        self, prefix=None, all_=False, sources=False, abspath=True
    ):
        """Show configuration options."""
        cmd_list = ['config', '--json']

        environ = self._set_environment_variables(prefix=prefix)
        if sources:
            cmd_list.append('--show-sources')
            worker = self._call_and_parse(
                cmd_list,
                abspath=abspath,
                callback=lambda o, e: self.
                _config_show_sources(o, e, prefix=prefix, all_=all_),
                environ=environ,
            )
        else:
            cmd_list.append('--show')
            worker = self._call_and_parse(
                cmd_list,
                abspath=abspath,
                environ=environ,
            )
        return worker

    def load_rc(self, path=None, prefix=None, system=False):
        """
        Load the raw conda configuration file using pyyaml.

        Depending on path or specific environment prefix and system that
        config file will be returned. If invalid or inexistent file, then an
        empty dicionary is returned.

        Parameters
        ----------
        path : str
            Path to conda configuration file.
        prefix : str
            Prefix path, to retrieve the specific prefix configuration file.
        system : bool
            Retrieve the system configuration file.
        """
        if path:
            config_path = path
        elif prefix and self.environment_exists(prefix=prefix):
            config_path = os.path.join(prefix, '.condarc')
        elif system:
            config_path = self.sys_rc_path
        elif not system:
            config_path = self.user_rc_path
        else:
            config_path = None

        data = {}
        if config_path and os.path.isfile(config_path):
            with open(config_path) as f:
                data = yaml.load(f)

        return data

    # --- Additional methods
    # -------------------------------------------------------------------------
    def dependencies(
        self, name=None, prefix=None, pkgs=None, channels=None, dep=True
    ):
        """Get dependenciy list for packages to be installed in an env."""
        if not pkgs or not isinstance(pkgs, (list, tuple)):
            raise TypeError(
                'must specify a list of one or more packages to '
                'install into existing environment'
            )

        cmd_list = ['install', '--dry-run', '--json', '--force-pscheck']

        if not dep:
            cmd_list.extend(['--no-deps'])

        if name:
            cmd_list.extend(['--name', name])
        elif prefix:
            cmd_list.extend(['--prefix', prefix])

        cmd_list.extend(pkgs)

        return self._call_and_parse(cmd_list)

    def environment_exists(
        self, name=None, prefix=None, abspath=True, log=True
    ):
        """Check if an environment exists by 'name' or by 'prefix'.

        If query is by 'name' only the default conda environments directory is
        searched.
        """
        if log:
            logger.debug(str((name, prefix)))

        if name and prefix or (name is None and prefix is None):
            raise TypeError("Exactly one of 'name' or 'prefix' is required.")

        if name:
            prefix = self.get_prefix_envname(name)

        if prefix is None:
            prefix = self.ROOT_PREFIX

        return os.path.isdir(os.path.join(prefix, 'conda-meta'))

    def clear_lock(self, abspath=True):
        """Clean any conda lock in the system."""
        cmd_list = ['clean', '--lock', '--json']
        return self._call_and_parse(cmd_list, abspath=abspath)

    def package_version(self, prefix=None, name=None, pkg=None, build=False):
        """Get installed package version in a given env."""
        package_versions = {}

        if name and prefix:
            raise TypeError("Exactly one of 'name' or 'prefix' is required.")

        if name:
            prefix = self.get_prefix_envname(name)

        if self.environment_exists(prefix=prefix):

            for package in self.linked(prefix):
                if pkg in package:
                    n, v, b = self.split_canonical_name(package)
                    if build:
                        package_versions[n] = '{0}={1}'.format(v, b)
                    else:
                        package_versions[n] = v

        return package_versions.get(pkg)

    @staticmethod
    def get_platform():
        """Get platform of current system (system and bitness)."""
        _sys_map = {
            'linux2': 'linux',
            'linux': 'linux',
            'darwin': 'osx',
            'win32': 'win',
            'openbsd5': 'openbsd',
        }

        non_x86_linux_machines = {'armv6l', 'armv7l', 'ppc64le'}
        sys_platform = _sys_map.get(sys.platform, 'unknown')
        bits = 8 * tuple.__itemsize__

        if (sys_platform == 'linux' and
                platform.machine() in non_x86_linux_machines):
            arch_name = platform.machine()
            subdir = 'linux-{0}'.format(arch_name)
        else:
            arch_name = {64: 'x86_64', 32: 'x86'}[bits]
            subdir = '{0}-{1}'.format(sys_platform, bits)

        return subdir

    def load_proxy_config(self, path=None, system=None):
        """Load the proxy configuration."""
        config = self.load_rc(path=path, system=system)

        proxy_servers = {}
        HTTP_PROXY = os.environ.get('HTTP_PROXY')
        HTTPS_PROXY = os.environ.get('HTTPS_PROXY')

        if HTTP_PROXY:
            proxy_servers['http'] = HTTP_PROXY

        if HTTPS_PROXY:
            proxy_servers['https'] = HTTPS_PROXY

        proxy_servers_conf = config.get('proxy_servers', {})
        proxy_servers.update(proxy_servers_conf)

        return proxy_servers

    def get_condarc_channels(
        self,
        normalize=False,
        conda_url='https://conda.anaconda.org',
        channels=None
    ):
        """Return all the channel urls defined in .condarc.

        If no condarc file is found, use the default channels.
        the `default_channel_alias` key is ignored and only the anaconda client
        `url` key is used.
        """
        # https://docs.anaconda.com/anaconda-repository/admin/reference
        # They can only exist on a system condarc
        # FIXME: Conda 4.2 now includes this key everywhere with the new
        # config system
        default_channels = self.load_rc(system=True).get(
            'default_channels', self.DEFAULT_CHANNELS
        )

        normalized_channels = []
        if channels is None:
            condarc = self.load_rc()
            channels = condarc.get('channels')

            if channels is None:
                channels = ['defaults']

        # FIXME: This is not taking into account that defaults might need to
        # be normalized as well
        if normalize:
            template = '{0}/{1}' if conda_url[-1] != '/' else '{0}{1}'
            for channel in channels:
                if channel == 'defaults':
                    normalized_channels += default_channels
                elif (channel.startswith('http://') or
                      channel.startswith('https://') or
                      channel.startswith('file://')):
                    normalized_channels.append(channel)
                else:
                    # Append to the conda_url that comes from anaconda client
                    # default_channel_alias key is deliberately ignored
                    normalized_channels.append(
                        template.format(conda_url, channel)
                    )
            channels = normalized_channels

        return channels

    # --- Pip commands
    # -------------------------------------------------------------------------
    def _call_pip(
        self, name=None, prefix=None, extra_args=None, callback=None
    ):
        """Call pip in QProcess worker."""
        cmd_list = self._pip_cmd(name=name, prefix=prefix)
        cmd_list.extend(extra_args)

        process_worker = ProcessWorker(cmd_list, pip=True, callback=callback)
        process_worker.sig_finished.connect(self._start)
        self._queue.append(process_worker)
        self._start()

        return process_worker

    def _pip_cmd(self, name=None, prefix=None):
        """Get pip location based on environment `name` or `prefix`."""
        if (name and prefix) or not (name or prefix):
            raise TypeError(
                "conda pip: exactly one of 'name' "
                "or 'prefix' "
                "required."
            )

        if name and self.environment_exists(name=name):
            prefix = self.get_prefix_envname(name)

        if sys.platform == 'win32':
            python = join(prefix, 'python.exe')  # FIXME:
            pip = join(prefix, 'pip.exe')  # FIXME:
        else:
            python = join(prefix, 'bin/python')
            pip = join(prefix, 'bin/pip')

        cmd_list = [python, pip]

        return cmd_list

    def pip_list(self, name=None, prefix=None, abspath=True):
        """Get list of pip installed packages."""
        if (name and prefix) or not (name or prefix):
            raise TypeError(
                "conda pip: exactly one of 'name' "
                "or 'prefix' "
                "required."
            )

        if name:
            prefix = self.get_prefix_envname(name)

        pip_command = os.sep.join([prefix, 'bin', 'python'])
        cmd_list = [pip_command, PIP_LIST_SCRIPT]
        process_worker = ProcessWorker(
            cmd_list,
            pip=True,
            parse=True,
            callback=self._pip_list,
            extra_kwargs={'prefix': prefix},
        )
        process_worker.sig_finished.connect(self._start)
        self._queue.append(process_worker)
        self._start()

        return process_worker

    def _pip_list(self, stdout, stderr, prefix=None):
        """Callback for `pip_list`."""
        result = stdout
        linked = self.linked(prefix)
        pip_only = []
        linked_names = [self.split_canonical_name(l)[0] for l in linked]

        for pkg in result:
            name = self.split_canonical_name(pkg)[0]
            if name not in linked_names:
                pip_only.append(pkg)
            # FIXME: NEED A MORE ROBUST WAY!
            #            if '<pip>' in line and '#' not in line:
            #                temp = line.split()[:-1] + ['pip']
            #                temp = '-'.join(temp)
            #                if '-(' in temp:
            #                    start = temp.find('-(')
            #                    end = temp.find(')')
            #                    substring = temp[start:end+1]
            #                    temp = temp.replace(substring, '')
            #                result.append(temp)

        return pip_only

    def pip_remove(self, name=None, prefix=None, pkgs=None):
        """Remove a pip package in given environment by `name` or `prefix`."""
        logger.debug(str((prefix, pkgs)))

        if isinstance(pkgs, (list, tuple)):
            pkg = ' '.join(pkgs)
        else:
            pkg = pkgs

        extra_args = ['uninstall', '--yes', pkg]

        return self._call_pip(name=name, prefix=prefix, extra_args=extra_args)

    def pip_search(self, search_string=None):
        """Search for pip packages in PyPI matching `search_string`."""
        extra_args = ['search', search_string]
        return self._call_pip(
            name='root',
            extra_args=extra_args,
            callback=self._pip_search,
        )

        # if stderr:
        #     raise PipError(stderr)
        # You are using pip version 7.1.2, however version 8.0.2 is available.
        # You should consider upgrading via the 'pip install --upgrade pip'
        # command.

    @staticmethod
    def _pip_search(stdout, stderr):
        """Callback for pip search."""
        result = {}
        lines = to_text_string(stdout).split('\n')
        while '' in lines:
            lines.remove('')

        for line in lines:
            if ' - ' in line:
                parts = line.split(' - ')
                name = parts[0].strip()
                description = parts[1].strip()
                result[name] = description

        return result

    def get_repodata(self, channels=None, pkgs_dirs=None):
        """Return repodata stored in conda cache files."""
        pkgs_dirs = pkgs_dirs or self.pkgs_dirs
        repodata_dic = {}
        all_paths = []
        paths_to_load = []

        official_pkgs_dirs = []
        for pkgs_dir in pkgs_dirs:
            cache = os.path.join(pkgs_dir, 'cache')
            try:
                open(os.path.join(pkgs_dir, 'urls.txt'), 'a').close()
                official_pkgs_dirs = [pkgs_dir]
                break
            except Exception:
                pass

        for pkgs_dir in official_pkgs_dirs:
            cache = os.path.join(pkgs_dir, 'cache')
            if os.path.isdir(cache):
                paths = [os.path.join(cache, p) for p in os.listdir(cache)]
                paths = [p for p in paths if os.path.isfile(p)]
                paths = [p for p in paths if p.endswith('.json')]
                all_paths.extend(paths)

            if channels:
                for channel in channels:
                    repodata_path = os.path.join(
                        cache, self.cache_fn_url(channel)
                    )
                    if repodata_path in all_paths:
                        paths_to_load.append(repodata_path)

        if channels is None:
            paths_to_load = all_paths

        mod_dates = {}
        for repodata_path in paths_to_load:
            with open(repodata_path, 'r') as f:
                raw_data = f.read()

            try:
                data = json.loads(raw_data)
            except Exception:
                data = {}

            # This key might not exist in a corrupt file
            url = data.get('_url')
            current_mod_date = os.path.getmtime(repodata_path)

            # If duplicate files for the same url on different cache locations
            # use the one with the latest modified date
            if url:
                if url in mod_dates:
                    previous_mod_date = mod_dates[url]
                    if current_mod_date > previous_mod_date:
                        mod_dates[url] = current_mod_date
                        repodata_dic[url] = data
                else:
                    mod_dates[url] = current_mod_date
                    repodata_dic[url] = data

        # for k, data in repodata_dic.items():
        #     print(k)
        #     pkgs = data['packages']
        #     for pkg, value in pkgs.items():
        #         if value['name'] == 'anaconda':
        #             print(value['version'])
        return repodata_dic

    def is_package_available(self, pkg, channels=None):
        """
        Check if a package is available for install based on cached repodata.
        """
        repodata = self.get_repodata(channels=channels)
        check = False
        for url, data in repodata.items():
            packages = [
                subdata.get('name', '')
                for cn, subdata in data.get('packages', {}).items()
            ]
            check = pkg in packages
            if check:
                break
        return check

    @staticmethod
    def cache_fn_url(url):
        """Return file name for channel fully normalized url."""
        # `url` must be right-padded with '/' to not invalidate existing caches
        if not url.endswith('/'):
            url += '/'
        md5 = hashlib.md5(ensure_binary(url)).hexdigest()
        return '{}.json'.format(md5[:8])


def CondaAPI():
    """Conda non blocking api."""
    global CONDA_API

    if CONDA_API is None:
        CONDA_API = _CondaAPI()

    return CONDA_API


COUNTER = 0


# --- Local testing
# -----------------------------------------------------------------------------
def ready_print(worker, output, error):  # pragma: no cover
    """Local test helper."""
    global COUNTER
    COUNTER += 1
    print(COUNTER, output, error)


def local_test():  # pragma: no cover
    """Run local test."""
    from anaconda_navigator.utils.qthelpers import qapplication

    app = qapplication()
    conda_api = CondaAPI()
    # print(conda_api.get_condarc_channels())
    # print(conda_api.get_condarc_channels(normalize=True))
    # print(conda_api.user_rc_path)
    # print(conda_api.sys_rc_path)
    # print(conda_api.load_rc())
    # worker = conda_api.config_add('channels', 'goanpeca')
    # print(conda_api.envs_dirs)
    # print(conda_api.pkgs_dirs)
    # notebook = conda_api.get_prefix_envname('notebook')
    # print(conda_api.envs_dirs_writable())
    # worker = conda_api.get_repodata(
    #     channels=["https://conda.anaconda.org/chdoig/osx-64"],
    # )
    # worker = conda_api.config_show()
    # prefix = '/Users/gpena-castellanos/anaconda/envs/notebook'
    # worker = conda_api.info(prefix=prefix)
    # worker.sig_finished.connect(ready_print)
    # worker = conda_api.config_show_sources(
    #     all_=True,
    #     prefix='/Users/gpena-castellanos/anaconda/envs/notebook',
    # )
    worker = conda_api._create_from_yaml(
        '/Users/gpena-castellanos/Desktop/requirements.yml',
        prefix='/Users/gpena-castellanos/anaconda/envs/boobo'
    )
    worker.sig_finished.connect(ready_print)

    # print(conda_api.proxy_servers())
    app.exec_()


if __name__ == '__main__':  # pragma: no cover
    local_test()
