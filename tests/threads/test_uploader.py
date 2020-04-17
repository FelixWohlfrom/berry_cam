import os
import time
import pytest

from http import HTTPStatus
from testfixtures import LogCapture

from berry_cam.threads.uploader import Uploader

TESTIMAGE = os.path.realpath(
    os.path.join(os.path.dirname(__file__), '..', 'test_data', 'test.jpg'))


def test_invalid_url():
    """
    Verifies that the thread stops after some time if an invalid sever url is given.
    """

    with LogCapture(names='berry_cam.threads.uploader') as log:
        uploader = Uploader('http://invalid_url', 'invalid_key', 2)
        uploader.start()
        uploader.upload_queue.put(TESTIMAGE)
        uploader.join(3)

        log.check_present(
            ('berry_cam.threads.uploader', 'ERROR',
             'Uploader: Error while connecting to server. Retrying...'),
            ('berry_cam.threads.uploader', 'ERROR',
             'Uploader: Failed to upload file after 2 tries, giving up. Are you sure the server is up?')
        )
        assert not uploader.is_alive()


def test_fast_fail_between_retries():
    """
    Verifies that if the thread stops fast after .stop() is called.
    """

    uploader = Uploader('http://invalid_url', 'invalid_key', 2)
    uploader.start()
    uploader.upload_queue.put(TESTIMAGE)
    uploader.stop()
    uploader.join(1.5)

    assert not uploader.is_alive()


def test_fast_fail_empty_queue():
    """
    Verifies that the thread stops even if the upload queue is empty.
    """

    uploader = Uploader('http://invalid_url', 'invalid_key', 2)
    uploader.start()
    uploader.stop()
    uploader.join(1.5)

    assert not uploader.is_alive()


def test_valid_url_invalid_api_key(requests_mock):
    """
    Verifies that the thread stops after some time if an invalid api key is given.

    :param requests_mock.Mocker requests_mock: The requests mocker
    """

    requests_mock.post('http://valid_url/', status_code=HTTPStatus.FORBIDDEN)

    with LogCapture(names='berry_cam.threads.uploader') as log:
        uploader = Uploader('http://valid_url', 'invalid_key', 2)
        uploader.start()
        uploader.upload_queue.put(TESTIMAGE)
        uploader.join(3)

        log.check_present(
            ('berry_cam.threads.uploader', 'ERROR',
             'Uploader: Access denied. Please check your api key.')
        )
        assert not uploader.is_alive()


def test_upload_success(requests_mock):
    """
    Verifies that correct data is sent on successful uploads.

    :param requests_mock.Mocker requests_mock: The requests mocker
    """

    requests_mock.post('http://valid_url/')

    with LogCapture(names='berry_cam.threads.uploader') as log:
        uploader = Uploader('http://valid_url', 'valid_key', 2)
        uploader.start()
        uploader.upload_queue.put(TESTIMAGE)
        time.sleep(1)
        uploader.stop()
        uploader.join(1.5)

        log.check_present(
            ('berry_cam.threads.uploader', 'INFO', 'Upload succeeded after 0 tries')
        )
        assert len(requests_mock.request_history) == 1
        assert b'api_key' in requests_mock.request_history[0].body
        assert b'valid_key' in requests_mock.request_history[0].body
        assert not uploader.is_alive()


def test_upload_failed_with_message(requests_mock):
    """
    Verifies that correct error message is logged on bad requests if only 'message' is set.

    :param requests_mock.Mocker requests_mock: The requests mocker
    """

    requests_mock.post(
        'http://valid_url', json={'message': 'Error message'}, status_code=int(HTTPStatus.BAD_REQUEST))

    with LogCapture(names='berry_cam.threads.uploader') as log:
        uploader = Uploader('http://valid_url', 'valid_key', 2)
        uploader.start()
        uploader.upload_queue.put(TESTIMAGE)
        time.sleep(1)
        uploader.stop()
        uploader.join(1.5)

        log.check_present(
            ('berry_cam.threads.uploader', 'ERROR',
             'Upload failed. Status code: {0}, message: Error message'.format(HTTPStatus.BAD_REQUEST))
        )
        assert not uploader.is_alive()


def test_upload_failed_with_message_and_errors(requests_mock):
    """
    Verifies that correct error message is logged on bad requests if 'message' and 'errors' is set.

    :param requests_mock.Mocker requests_mock: The requests mocker
    """

    requests_mock.post(
        'http://valid_url',
        json={'message': 'Error message', 'errors': 'Additional errors'},
        status_code=int(HTTPStatus.BAD_REQUEST))

    with LogCapture(names='berry_cam.threads.uploader') as log:
        uploader = Uploader('http://valid_url', 'valid_key', 2)
        uploader.start()
        uploader.upload_queue.put(TESTIMAGE)
        time.sleep(1)
        uploader.stop()
        uploader.join(1.5)

        log.check_present(
            ('berry_cam.threads.uploader', 'ERROR',
             'Upload failed. Status code: {0}, message: Error message'.format(HTTPStatus.BAD_REQUEST))
        )
        log.check_present(
            ('berry_cam.threads.uploader', 'ERROR', 'Additional errors')
        )
        assert not uploader.is_alive()


def test_upload_failed_with_other_failure(requests_mock):
    """
    Verifies that correct error message is logged on other failure messages than 'message' or 'errors'.

    :param requests_mock.Mocker requests_mock: The requests mocker
    """

    requests_mock.post(
        'http://valid_url', json='Other failure', status_code=int(HTTPStatus.BAD_REQUEST))

    with LogCapture(names='berry_cam.threads.uploader') as log:
        uploader = Uploader('http://valid_url', 'valid_key', 2)
        uploader.start()
        uploader.upload_queue.put(TESTIMAGE)
        time.sleep(1)
        uploader.stop()
        uploader.join(1.5)

        log.check_present(
            ('berry_cam.threads.uploader', 'ERROR',
             "Upload failed. Status code: {0}, message: b'\"Other failure\"'".format(HTTPStatus.BAD_REQUEST))
        )
        assert not uploader.is_alive()
