# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Tests for conda API functions."""

# yapf: disable

# Standard library imports
import os
import random
import sys

# Third party imports
from qtpy.QtCore import Qt  # analysis:ignore
import pytest

# Local imports
from anaconda_navigator.api.anaconda_api import AnacondaAPI
from anaconda_navigator.api.conda_api import CondaEnvExistsError, _CondaAPI
from anaconda_navigator.utils.fixtures import tmpfolder  # analysis:ignore


# yapf: enable

xfail = pytest.mark.xfail

# --- Constants
# -----------------------------------------------------------------------------
DEFAULT_TIMEOUT = 1200000  # 1 minute
OUTPUT_KEYS = ['success', 'actions']
OUTPUT_KEYS_CLONE = ['success']
CONFIG_GET_KEYS = [
    'add_anaconda_token',
    'add_binstar_token',
    'add_pip_as_python_dependency',
    'allow_other_channels',
    'allow_softlinks',
    'always_copy',
    'always_softlink',
    'always_yes',
    'anaconda_upload',
    'auto_update_conda',
    'binstar_upload',
    'changeps1',
    'channel_priority',
    'channels',
    'create_default_packages',
    'default_channels',
    'disallow',
    'envs_dirs',
    'offline',
    'pinned_packages',
    'pkgs_dirs',
    'shortcuts',
    'show_channel_urls',
    'track_features',
    'update_dependencies',
    'use_pip',
]


# --- Helpers
# -----------------------------------------------------------------------------
def python_version():
    """Helper method that returns the current python version."""
    return '.'.join(str(i) for i in sys.version_info[:3])


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture(scope="module")
def api():
    api = _CondaAPI()
    return api


#@pytest.fixture
#def manager(qtbot):
#    api = AnacondaAPI()
#    envs = api.conda_get_envs()
#    env_names = [env.rsplit(os.sep, 1)[-1] for env in envs]
#    if 'navigator_test' in env_names:
#        index = env_names.index('navigator_test')
#        import shutil
#        shutil.rmtree(envs[index], ignore_errors=True)
#    return qtbot, api
#
#
## --- Tests
## -----------------------------------------------------------------------------
#def test_create_yaml(manager, tmpfolder):
#    qtbot, api = manager
#    myfile = os.path.join(tmpfolder, 'env.yaml')
#    version = os.environ.get('TRAVIS_PYTHON_VERSION', None)
#    if version:
#        vers = "=" + version
#    else:
#        vers = ""
#    with open(myfile, 'w') as f:
#        f.write(
#            "name: navigator_test\n"
#            "dependencies:\n    - python{}\n".format(vers)
#        )
#    worker = api.conda_create_yaml('navigator_test', myfile)
#    with qtbot.waitSignal(worker.sig_finished, DEFAULT_TIMEOUT * 2, True):
#        worker.start()
#    env_names = [env.rsplit(os.sep, 1)[-1] for env in api.conda_get_envs()]
#    assert 'navigator_test' in env_names


def test_worker(qtbot, api):
    pass


def test_call_conda(qtbot, api):
    pass
    # extra_args, abspath=True, parse=False, callback=None


def test_call_and_parse(qtbot, api):
    # extra_args, abspath=True, callback=None
    pass


def test_setup_install_commands_from_kwargs(qtbot, api):
    # kwargs, keys=tuple()
    pass


def test_set_root_prefix(qtbot, api):
    pass
    # prefix=None


def test_get_conda_version(qtbot, api):
    def worker_ready(worker, output, error):
        assert (
            output.startswith('4.3.') or output.startswith('4.4.')
            or output.startswith('4.5.') or output.startswith('4.6.')
        )

    worker = api.get_conda_version()
    worker.sig_finished.connect(worker_ready)
    with qtbot.waitSignal(worker.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass


def test_get_conda_version_callback(qtbot, api):
    pass
    # stdout, stderr


def test_test_envs_dirs(qtbot, api):
    pass


def test_get_envs(qtbot, api):
    pass
    # log=True


def test_get_prefix_envname(qtbot, api):
    pass
    # name


def test_linked(qtbot):
    # prefix, apps=False
    pass


def test_linked_apps_info(qtbot, api):
    pass
    # prefix


def test_split_canonical_name(qtbot, api):
    def r(mult=10):
        return str(int(random.random() * mult))

    name = 'package' + r(100000000)
    version = [r(), r(), r(), r(), r(), r()]
    version = '.'.join(version)
    build = 'somebuild' + '_' + r(100)
    package_canonical_name = '-'.join([name, version, build])

    n, v, b = api.split_canonical_name(package_canonical_name)

    print(name, version, build)
    print(package_canonical_name)
    print(n, v, b)

    assert name == n
    assert version == v
    assert build == b


def test_info(qtbot, api):
    USED_KEYS = [
        "channels",
        "conda_build_version",
        "conda_env_version",
        # "conda_location",  # This key is new and not used
        "conda_prefix",
        "conda_private",
        "conda_version",
        "default_prefix",
        "env_vars",
        "envs",
        "envs_dirs",
        "offline",
        "pkgs_dirs",
        "platform",
        "python_version",
        "rc_path",
        "requests_version",
        "root_prefix",
        "root_writable",
        "site_dirs",
        "sys.executable",
        "sys.prefix",
        "sys.version",
        "sys_rc_path",
        "user_agent",
        "user_rc_path",
    ]

    def worker_ready(worker, output, error):
        print('Output:', output)
        print('Error:', error)
        assert not bool(error)  # Check that error is empty '' or None
        assert isinstance(output, dict)
        for key in USED_KEYS:
            # Check the keys have not changed
            assert key in output

    worker = api.info()
    worker.sig_finished.connect(worker_ready)
    with qtbot.waitSignal(worker.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass


def test_package_info(qtbot, api):
    pass
    # package, abspath=True


def test_search(qtbot, api):
    pass
    # regex=None, spec=None, **kwargs


def test_create_from_yaml(qtbot, api):
    pass
    # name, yamlfile


def test_create_invalid(qtbot, api):
    with pytest.raises(TypeError):
        api.create(pkgs=['python'])

    with pytest.raises(TypeError):
        api.create(name='name', prefix='prefix')

    with pytest.raises(TypeError):
        api.create(name='name', prefix='prefix', pkgs=set('python'))

    with pytest.raises(TypeError):
        api.create(prefix='prefix')

    with pytest.raises(TypeError):
        api.create(name='name')

    with pytest.raises(CondaEnvExistsError):
        api.create(name='test', pkgs=['python'])


def test_create_remove_name(qtbot, api):
    def worker_ready2(worker, output, error):
        print('Output:', output)
        print('Error:', error)
        assert not bool(error)
        assert isinstance(output, dict)

    def worker_ready(worker, output, error):
        print('Output:', output)
        print('Error:', error)
        assert not bool(error)
        assert isinstance(output, dict)
        for key in OUTPUT_KEYS:
            assert key in output
        assert output.get('success')

        worker_r = api.remove_environment(name=worker.test_name)
        worker.sig_finished.connect(worker_ready2)
        with qtbot.waitSignal(worker_r.sig_finished, timeout=DEFAULT_TIMEOUT):
            pass

    pkgs = ['python=' + python_version()]
    name = 'testenv_' + str(int(random.random() * 10000000))
    worker = api.create(name=name, pkgs=pkgs)
    worker.test_name = name
    worker.sig_finished.connect(worker_ready)
    with qtbot.waitSignal(worker.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass


def test_create_remove_prefix(qtbot, api):
    def worker_ready2(worker, output, error):
        print('Output:', output)
        print('Error:', error)
        assert not bool(error)
        assert isinstance(output, dict)

    def worker_ready(worker, output, error):
        print('Output:', output)
        print('Error:', error)
        assert not bool(error)
        assert isinstance(output, dict)
        for key in OUTPUT_KEYS:
            assert key in output
        assert output.get('success')

        worker_r = api.remove_environment(prefix=worker.test_prefix)
        worker.sig_finished.connect(worker_ready2)
        with qtbot.waitSignal(worker_r.sig_finished, timeout=DEFAULT_TIMEOUT):
            pass

    pkgs = ['python=' + python_version()]
    name = 'testenv_' + str(int(random.random() * 10000000))
    prefix = os.path.join(api.ROOT_PREFIX, 'envs', name)
    worker = api.create(prefix=prefix, pkgs=pkgs)
    worker.test_prefix = prefix
    worker.sig_finished.connect(worker_ready)
    with qtbot.waitSignal(worker.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass


def test_parse_token_channel(qtbot, api):
    pass
    # channel, token


def test_install_dry_keys(qtbot, api):
    """Conda 4.3 used a list for the actions, 4.4 uses a dict."""

    def worker_ready_3(worker, output, error):
        print('Output:', output)
        print('Error:', error)
        assert isinstance(output, dict)
        assert 'success' in output

    def worker_ready_2(worker, output, error):
        print('Output:', output)
        print('Error:', error)
        assert isinstance(output, dict)
        assert 'success' in output
        assert 'actions' in output
        actions = output.get('actions')
        assert isinstance(actions, dict)
        assert output.get('success')

        worker = api.remove_environment(prefix=worker.test_prefix)
        worker.sig_finished.connect(worker_ready_3)
        with qtbot.waitSignal(worker.sig_finished, timeout=DEFAULT_TIMEOUT):
            pass

    def worker_ready(worker, output, error):
        print('Output:', output)
        print('Error:', error)
        assert isinstance(output, dict)
        assert 'success' in output

        pkgs = ['pylint']
        worker = api.install(
            prefix=worker.test_prefix, pkgs=pkgs, dry_run=True
        )
        worker.test_prefix = prefix
        worker.sig_finished.connect(worker_ready_2)
        with qtbot.waitSignal(worker.sig_finished, timeout=DEFAULT_TIMEOUT):
            pass

    pkgs = ['python=' + python_version()]
    name = 'testenv_' + str(int(random.random() * 10000000))
    prefix = os.path.join(api.ROOT_PREFIX, 'envs', name)
    worker = api.create(prefix=prefix, pkgs=pkgs)
    worker.test_prefix = prefix
    worker.sig_finished.connect(worker_ready)
    with qtbot.waitSignal(worker.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass


def test_update(qtbot, api):
    pass
    # *pkgs, **kwargs


def test_remove(qtbot, api):
    pass
    # name=None, prefix=None, pkgs=None, all_=False


def test_remove_environment(qtbot, api):
    pass
    # name=None, path=None, **kwargs


def test_clone_environment(qtbot, api):
    def worker_ready(worker, output, error):
        print('Output:', output)
        print('Error:', error)
        assert not bool(error)
        assert isinstance(output, dict)
        for key in OUTPUT_KEYS_CLONE:
            assert key in output
        assert output.get('success')

    pkgs = ['python=' + python_version()]
    name = 'testenv_' + str(int(random.random() * 10000000))
    clone_from_prefix = os.path.join(api.ROOT_PREFIX, 'envs', name)
    worker = api.create(prefix=clone_from_prefix, pkgs=pkgs)
    with qtbot.waitSignal(worker.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass

    clone_prefix = clone_from_prefix + '_clone'
    worker_c = api.clone_environment(clone_from_prefix, prefix=clone_prefix)
    worker_c.sig_finished.connect(worker_ready)
    with qtbot.waitSignal(worker_c.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass


def test_clone_invalid(api):
    with pytest.raises(TypeError):
        api.clone_environment('clone', name='name', prefix='prefix')

    with pytest.raises(TypeError):
        api.clone_environment('clone')


def test_setup_config_from_kwargs(qtbot, api):
    pass


def test_config_set_valid(qtbot, api):
    def worker_ready(worker, output, error):
        print('Output:', output)
        print('Error:', error)
        assert not bool(error)
        assert output.get('always_yes')
        tests = []
        for key in CONFIG_GET_KEYS:
            tests.append(key in output)
        assert any(tests)

    worker = api.config_set('always_yes', True)
    with qtbot.waitSignal(worker.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass

    worker_get = api.config_get(*CONFIG_GET_KEYS)
    worker_get.sig_finished.connect(worker_ready)
    with qtbot.waitSignal(worker_get.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass

    worker_2 = api.config_set('always_yes', False)
    with qtbot.waitSignal(worker_2.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass


def test_config_set_invalid(qtbot, api):
    def worker_ready(worker, output, error):
        print('Output:', output)
        print('Error:', error)
        assert 'is not a known primitive parameter' in error
        assert not bool(output)

    worker = api.config_set('random_key', True)
    worker.sig_finished.connect(worker_ready)
    with qtbot.waitSignal(worker.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass


def test_config_add_remove_delete(qtbot, api):
    channel = 'somefakechannel_' + str(int(random.random() * 1000))

    def worker_ready_get_add(worker, output, error):
        print('Output:', output)
        print('Error:', error)
        assert not bool(error)
        channels = output.get('channels')
        assert isinstance(channels, list)
        assert channel in channels

    worker_add = api.config_add('channels', channel)
    with qtbot.waitSignal(worker_add.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass

    worker_get = api.config_get(*CONFIG_GET_KEYS)
    worker_get.sig_finished.connect(worker_ready_get_add)
    with qtbot.waitSignal(worker_get.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass

    def worker_ready_get_remove(worker, output, error):
        print('Output:', output)
        print('Error:', error)
        assert not bool(error)
        channels = output.get('channels')
        assert isinstance(channels, list)
        assert channel not in channels

    worker_rem = api.config_remove('channels', channel)
    with qtbot.waitSignal(worker_rem.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass

    worker_get_2 = api.config_get(*CONFIG_GET_KEYS)
    worker_get_2.sig_finished.connect(worker_ready_get_remove)
    with qtbot.waitSignal(worker_get_2.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass

    def worker_ready_get_delete(worker, output, error):
        print('Output:', output)
        print('Error:', error)
        assert not bool(error)
        assert output.get('channels') is None

    worker_delete = api.config_delete('channels')
    with qtbot.waitSignal(worker_delete.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass

    worker_get_3 = api.config_get(*CONFIG_GET_KEYS)
    worker_get_3.sig_finished.connect(worker_ready_get_delete)
    with qtbot.waitSignal(worker_get_3.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass


# --- Additional methods
# -----------------------------------------------------------------------------
def test_dependencies(qtbot, api):
    pass  # name=None, prefix=None, pkgs=None, channels=None, dep=True


def test_environment_exists(qtbot, api):
    with pytest.raises(TypeError):
        api.environment_exists()

    assert api.environment_exists(name='root')
    assert api.environment_exists(name='test')
    assert api.environment_exists(prefix=api.ROOT_PREFIX)
    assert api.environment_exists(
        prefix=os.path.join(api.ROOT_PREFIX, 'envs', 'test')
    )


@xfail
def test_clear_lock(qtbot, api):
    def worker_ready(worker, output, error):
        print('Output:', output)
        print('Error:', error)
        assert output.get('success')
        assert not bool(error)

    worker = api.clear_lock()
    worker.sig_finished.connect(worker_ready)
    with qtbot.waitSignal(worker.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass


def test_package_version(qtbot, api):
    pass
    # prefix=None, name=None, pkg=None, build=False


def test_get_platform(qtbot, api):
    pass


def test_load_rc(qtbot, api):
    pass


def load_proxy_config(qtbot, api):
    pass
    # self, path=None, system=None


def test_get_condarc_channels(qtbot, api):
    # TODO:
    pass


# --- Pip commands
# -------------------------------------------------------------------------
def test_call_pip(qtbot, api):
    pass
    # name=None, prefix=None, extra_args=None, callback=None


def test_pip_cmd(qtbot, api):
    pass
    # self, name=None, prefix=None


def test_pip_list(qtbot, api):
    pass
    #conda_api.pip_list(name=None, prefix=None, abspath=True)


def test_pip_list_callback(qtbot, api):
    pass
    #conda_api._pip_list(stdout, stderr, prefix)


def test_pip_remove(qtbot, api):
    pass
    #conda_api.pip_remove(name=name, prefix=prefix, pkgs=pkgs)


def test_pip_search(qtbot, api):
    pass
    #conda_api.pip_search(search_string=search_string)


def test_pip_search_callback(qtbot, api):
    pass
    #conda_api._pip_search(stdout, stderr)
