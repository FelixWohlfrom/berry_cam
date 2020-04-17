import time
import pytest

from http import HTTPStatus
from testfixtures import LogCapture

from berry_cam.threads.settings_loader import SettingsLoader


def test_invalid_url():
    """
    Verifies that the thread stops after some time if an invalid sever url is given.
    """

    with LogCapture(names='berry_cam.threads.settings_loader') as log:
        settings_loader = SettingsLoader(
            'Test-Camera', 'http://invalid_url', 'invalid_key', 2)
        settings_loader.start()
        settings_loader.join(3)

        log.check_present(
            ('berry_cam.threads.settings_loader', 'ERROR',
             'Settings loader: Error while connecting to server. Retrying...'),
            ('berry_cam.threads.settings_loader', 'ERROR',
             'Settings loader: Failed to get settings after 2 tries, giving up. Are you sure the server is up?')
        )
        assert not settings_loader.is_alive()


def test_fast_fail_between_retries():
    """
    Verifies that if the thread stops fast after .stop() is called.
    """

    settings_loader = SettingsLoader(
        'Test-Camera', 'http://invalid_url', 'invalid_key', 2)
    settings_loader.start()
    time.sleep(0.5)
    settings_loader.stop()
    settings_loader.join(1.5)

    assert not settings_loader.is_alive()


def test_valid_url_invalid_api_key(requests_mock):
    """
    Verifies that the thread stops after some time if an invalid api key is given.

    :param requests_mock.Mocker requests_mock: The requests mocker
    """

    requests_mock.get('http://valid_url/', status_code=HTTPStatus.FORBIDDEN)

    with LogCapture(names='berry_cam.threads.settings_loader') as log:
        settings_loader = SettingsLoader(
            'Test-Camera', 'http://valid_url', 'invalid_key', 2)
        settings_loader.start()
        settings_loader.join(3)

        log.check_present(
            ('berry_cam.threads.settings_loader', 'ERROR',
             'Settings loader: Access denied. Please check your api key.')
        )
        assert not settings_loader.is_alive()


def test_valid_url_valid_api_key(requests_mock):
    """
    Verifies that a heartbeat is properly send on an valid url and a valid key.

    :param requests_mock.Mocker requests_mock: The requests mocker
    """

    requests_mock.get('http://valid_url/', json={'enabled': True})

    class test_updater:
        enabled = False

    with LogCapture(names='berry_cam.threads.settings_loader') as log:
        settings_loader = SettingsLoader(
            'Test-Camera', 'http://valid_url', 'valid_key', 2, [test_updater])
        settings_loader.start()
        time.sleep(1)
        settings_loader.stop()
        settings_loader.join(1.5)

        assert test_updater.enabled == True
        log.check_present(
            ('berry_cam.threads.settings_loader', 'DEBUG',
             "Settings loader: Read setting 'enabled': True")
        )
        assert not settings_loader.is_alive()

# @pytest.mark.skip(reason="Takes really long")
def test_send_multiple_updates(requests_mock):
    """
    Verify that reading different settings from the server works within a single thread.

    :param requests_mock.Mocker requests_mock: The requests mocker
    """

    requests_mock.get('http://valid_url/', json={'enabled': True})

    class test_updater:
        enabled = False

    with LogCapture(names='berry_cam.threads.settings_loader') as log:
        settings_loader = SettingsLoader(
            'Test-Camera', 'http://valid_url', 'valid_key', 2, [test_updater])
        settings_loader.start()
        time.sleep(1)
        assert test_updater.enabled == True

        requests_mock.get('http://valid_url/', json={'enabled': False})
        time.sleep(10)
        settings_loader.stop()
        settings_loader.join(1.5)

        assert test_updater.enabled == False
        log.check_present(
            ('berry_cam.threads.settings_loader', 'DEBUG',
             "Settings loader: Read setting 'enabled': True"),
            ('berry_cam.threads.settings_loader', 'DEBUG',
             "Settings loader: Read setting 'enabled': False")
        )
        assert not settings_loader.is_alive()
