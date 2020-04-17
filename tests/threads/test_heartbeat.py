import time
import pytest

from http import HTTPStatus
from testfixtures import LogCapture

from berry_cam.threads.heartbeat import Heartbeat


def test_invalid_url():
    """
    Verifies that the thread stops after some time if an invalid sever url is given.
    """

    with LogCapture(names='berry_cam.threads.heartbeat') as log:
        heartbeat = Heartbeat(
            'Test-Camera', 'http://invalid_url', 'invalid_key', 2)
        heartbeat.start()
        heartbeat.join(3)

        log.check_present(
            ('berry_cam.threads.heartbeat', 'ERROR',
             'Heartbeat: Error while connecting to server. Retrying...'),
            ('berry_cam.threads.heartbeat', 'ERROR',
             'Heartbeat: Failed to send heartbeat after 2 tries, giving up. Are you sure the server is up?')
        )
        assert not heartbeat.is_alive()


def test_fast_fail_between_retries():
    """
    Verifies that if the thread stops fast after .stop() is called.
    """

    heartbeat = Heartbeat(
        'Test-Camera', 'http://invalid_url', 'invalid_key', 2)
    heartbeat.start()
    time.sleep(0.5)
    heartbeat.stop()
    heartbeat.join(1.5)

    assert not heartbeat.is_alive()


def test_valid_url_invalid_api_key(requests_mock):
    """
    Verifies that the thread stops after some time if an invalid api key is given.

    :param requests_mock.Mocker requests_mock: The requests mocker
    """

    requests_mock.post('http://valid_url/', status_code=HTTPStatus.FORBIDDEN)

    with LogCapture(names='berry_cam.threads.heartbeat') as log:
        heartbeat = Heartbeat(
            'Test-Camera', 'http://valid_url', 'invalid_key', 2)
        heartbeat.start()
        heartbeat.join(3)

        log.check_present(
            ('berry_cam.threads.heartbeat', 'ERROR',
             'Heartbeat: Access denied. Please check your api key.')
        )
        assert len(requests_mock.request_history) == 1
        assert requests_mock.request_history[0].body == 'name=Test-Camera&api_key=invalid_key&enabled=False'
        assert not heartbeat.is_alive()


def test_valid_url_valid_api_key(requests_mock):
    """
    Verifies that a heartbeat is properly send on an valid url and a valid key.

    :param requests_mock.Mocker requests_mock: The requests mocker
    """

    requests_mock.post('http://valid_url/')

    with LogCapture(names='berry_cam.threads.heartbeat') as log:
        heartbeat = Heartbeat(
            'Test-Camera', 'http://valid_url', 'valid_key', 2)
        heartbeat.start()
        time.sleep(1)
        heartbeat.stop()
        heartbeat.join(1.5)

        log.check_present(
            ('berry_cam.threads.heartbeat', 'DEBUG', 'Heartbeat sent.')
        )
        assert len(requests_mock.request_history) == 1
        assert requests_mock.request_history[0].body == 'name=Test-Camera&api_key=valid_key&enabled=False'
        assert not heartbeat.is_alive()


# @pytest.mark.skip(reason="Takes really long")
def test_send_multiple_hearbeats(requests_mock):
    """
    Verifies that multiple hearbeats will be sent with different data.

    :param requests_mock.Mocker requests_mock: The requests mocker
    """

    requests_mock.post('http://valid_url/')

    with LogCapture(names='berry_cam.threads.heartbeat') as log:
        heartbeat = Heartbeat(
            'Test-Camera', 'http://valid_url', 'valid_key', 2)
        heartbeat.start()
        time.sleep(10)
        heartbeat.enabled = True
        time.sleep(25)
        heartbeat.stop()
        heartbeat.join(1.5)

        log.check_present(
            ('berry_cam.threads.heartbeat', 'DEBUG', 'Heartbeat sent.')
        )
        assert len(requests_mock.request_history) == 2
        assert requests_mock.request_history[0].body == 'name=Test-Camera&api_key=valid_key&enabled=False'
        assert requests_mock.request_history[1].body == 'name=Test-Camera&api_key=valid_key&enabled=True'
        assert not heartbeat.is_alive()
