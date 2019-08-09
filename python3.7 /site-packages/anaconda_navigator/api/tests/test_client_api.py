# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Api client tets."""

# yapf: disable

# Standard library imports
import os

# Third party imports
from flaky import flaky
import pytest

# Local imports
from anaconda_navigator.api import client_api
from anaconda_navigator.api.client_api import ClientAPI, ClientWorker


# yapf: enable

NAVIGATOR_TEST_USERNAME = os.environ.get('NAVIGATOR_TEST_USERNAME', )
NAVIGATOR_TEST_PASSWORD = os.environ.get('NAVIGATOR_TEST_PASSWORD')

# Constants used in tests
USER_KEYS = ['created_at', 'location', 'user_type', 'company', 'url', 'name']
DEFAULT_TIMEOUT = 10000

skipif = pytest.mark.skipif
xfail = pytest.mark.xfail


def test_dependencies():
    deplist = ['python 3.5*', 'qt 5.6.0', 'sip >=4.18']

    assert not client_api.is_dependency_met(deplist, '4.17.1', 'sip')
    assert client_api.is_dependency_met(deplist, '4.18', 'sip')
    assert client_api.is_dependency_met(deplist, '4.25.5', 'sip')

    assert client_api.is_dependency_met(deplist, '3.5', 'python')
    assert client_api.is_dependency_met(deplist, '3.5.1', 'python')
    assert not client_api.is_dependency_met(deplist, '3.4.5', 'python')

    assert client_api.is_dependency_met(deplist, '5.6.0', 'qt')
    assert not client_api.is_dependency_met(deplist, '5.6.0.1', 'python')
    assert not client_api.is_dependency_met(deplist, '5.7', 'python')
    assert not client_api.is_dependency_met(deplist, '5.5.9', 'python')


@flaky(max_runs=4, min_passes=1)
@skipif(
    NAVIGATOR_TEST_PASSWORD is None,
    reason='User and password are available as env variables on CI'
)
def test_login(qtbot):
    def _worker_output_ready(worker, output, error):
        print('Output', output)
        print('Error', error)
        assert output is not None
        assert len(output) >= 39
        assert error is None

    api = ClientAPI()
    api.logout()

    worker_login = api.login(
        NAVIGATOR_TEST_USERNAME,
        NAVIGATOR_TEST_PASSWORD,
        'navigator-tests',
        '',
    )
    worker_login.sig_finished.connect(_worker_output_ready)
    with qtbot.waitSignal(worker_login.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass


def test_login_bad_password(qtbot):
    def _worker_output_ready(worker, output, error):
        print('Output', output)
        print('Error', error)
        assert output is None
        assert error is not None
        assert 'invalid credentials' in error.lower()
        assert '401' in error

    api = ClientAPI()
    api.set_ssl(True)
    worker = api.login('goanpeca', 'badpass', 'navigator-tests', '')
    worker.sig_finished.connect(_worker_output_ready)

    with qtbot.waitSignal(worker.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass


def test_login_bad_username(qtbot):
    def _worker_output_ready(worker, output, error):
        print('Output', output)
        print('Error', error)
        assert output is None
        assert error is not None
        assert 'this user is not enabled to log in' in error.lower()
        assert '401' in error

    api = ClientAPI()
    worker = api.login('adsasdasdxzcasdasda', 'badpass', 'navigator-tests', '')
    worker.sig_finished.connect(_worker_output_ready)

    with qtbot.waitSignal(worker.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass


@skipif(
    NAVIGATOR_TEST_PASSWORD is None,
    reason='User and password are available as env variables on CI'
)
def test_load_licenses(qtbot):
    def _worker_output_ready(worker, output, error):
        print('Output', output)
        print('Error', error)
        assert error is None
        assert isinstance(output, (list))
        if len(output) > 0:
            assert len(output) == 4

    api = ClientAPI()
    api.logout()

    worker = api.login(
        NAVIGATOR_TEST_USERNAME, NAVIGATOR_TEST_PASSWORD, 'Test', ''
    )
    with qtbot.waitSignal(worker.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass

    worker_licenses = api.get_user_licenses()
    worker_licenses.sig_finished.connect(_worker_output_ready)
    with qtbot.waitSignal(worker_licenses.sig_finished, timeout=10000):
        pass

    # Now check the methods alone not via the worker
    licenses = api._get_user_licenses()
    assert isinstance(licenses, (list))
    if len(licenses) > 0:
        assert len(licenses) == 4


def test_api_url():
    api = ClientAPI()
    beta = 'https://api.beta.anaconda.org'
    default = 'https://api.anaconda.org'

    # Switch from beta and back
    api.set_api_url(beta)
    assert api.get_api_url() == beta
    api.set_api_url(default)
    assert api.get_api_url() == default


@flaky(max_runs=4, min_passes=1)
def test_user_logout(qtbot):
    api = ClientAPI()
    api.logout()

    worker = api.login(
        NAVIGATOR_TEST_USERNAME, NAVIGATOR_TEST_PASSWORD, 'Test', ''
    )
    with qtbot.waitSignal(worker.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass
    api.logout()

    user = api.user()
    print('Logout user:', user)
    assert isinstance(user, dict)
    assert len(user) == 0


@flaky(max_runs=4, min_passes=1)
@skipif(
    NAVIGATOR_TEST_PASSWORD is None,
    reason='User and password are available as env variables on CI'
)
def test_user_login(qtbot):
    api = ClientAPI()
    api.logout()
    worker_login = api.login(
        NAVIGATOR_TEST_USERNAME, NAVIGATOR_TEST_PASSWORD, 'navigator-tests', ''
    )
    with qtbot.waitSignal(worker_login.sig_finished, timeout=DEFAULT_TIMEOUT):
        pass
    user = api.user()
    print(user)
    assert isinstance(user, dict)
    assert user.get('login') == NAVIGATOR_TEST_USERNAME
    for key in USER_KEYS:
        assert key in user


@skipif(
    NAVIGATOR_TEST_PASSWORD is None,
    reason='User and password are available as env variables on CI'
)
def test_org_login(qtbot):
    api = ClientAPI()
    api.logout()
    worker_login = api.login(
        NAVIGATOR_TEST_USERNAME, NAVIGATOR_TEST_PASSWORD, 'navigator-tests', ''
    )
    with qtbot.waitSignal(
        worker_login.sig_finished, timeout=DEFAULT_TIMEOUT
    ) as blocker:
        blocker
    login = 'goanpeca'
    user = api.organizations(login=login)
    print(user)
    assert isinstance(user, dict)
    assert user.get('login') == login
    for key in USER_KEYS:
        assert key in user


def test_ssl():
    api = ClientAPI()
    default = True
    test = False
    # Switch from beta and back
    api.set_ssl(test)
    assert api.get_ssl() == test
    api.set_ssl(default)
    assert api.get_ssl() == default


def test_client_worker_succeeds(qtbot):
    exception_text = 'Text of exception'

    def method(*args, **kwargs):
        raise Exception('(' + exception_text + ')')

    def worker_ready(worker, output, error):
        print('Output', output)
        print('Error', error)
        assert output is None
        assert exception_text in error

    worker = ClientWorker(method, (1, ), {'test': 2})
    worker.sig_finished.connect(worker_ready)

    assert not worker.is_finished()

    with qtbot.waitSignal(
        worker.sig_finished, timeout=DEFAULT_TIMEOUT
    ) as blocker:
        worker.start()
        blocker

    assert worker.is_finished()


def test_client_worker_fails(qtbot):
    def method(*args, **kwargs):
        return [args, kwargs]

    def worker_ready(worker, output, error):
        print('Output', output)
        print('Error', error)
        assert error is None
        assert [(1, ), {'test': 2}] == output

    worker = ClientWorker(method, (1, ), {'test': 2})
    worker.sig_finished.connect(worker_ready)

    assert not worker.is_finished()

    with qtbot.waitSignal(
        worker.sig_finished, timeout=DEFAULT_TIMEOUT
    ) as blocker:
        worker.start()
        blocker

    assert worker.is_finished()


def test_domain():
    # TODO:
    pass


def test_load_repodata():
    # TODO:
    pass
