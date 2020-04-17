import time
import pytest

from queue import Queue
from http import HTTPStatus
from testfixtures import LogCapture

from berry_cam.threads.uploader import DeleteProtectedQueue


@pytest.fixture
def test_queue_values():
    """
    Returns a python Queue with some values in it.
    """
    queue = Queue()
    for i in range(5):
        queue.put(i)
    return queue


@pytest.fixture
def test_queue(test_queue_values):
    """
    Returns a DeleteProtectedQueue with some values in it.
    To be used in the testcases.
    """
    return DeleteProtectedQueue(test_queue_values)


def test_constructor(test_queue, test_queue_values):
    """
    Test the constructor for the DeleteProtectedQueue.

    :param DeleteProtectedQueue test_queue: The queue to verifiy.
    :param Queue test_queue_values: The original values stored in the
                                    DeleteProtectedQueue
    """

    assert test_queue is not None
    assert test_queue.qsize() == test_queue_values.qsize()


def test_adding_values(test_queue, test_queue_values):
    """
    Test adding elements to the DeleteProtectedQueue.

    :param DeleteProtectedQueue test_queue: The queue to verifiy.
    :param Queue test_queue_values: The original values stored in the
                                    DeleteProtectedQueue
    """

    old_queue_size = test_queue.qsize()

    test_queue.put('foo')

    assert test_queue.qsize() == old_queue_size + 1
    assert test_queue.qsize() == test_queue_values.qsize()


def test_removing_values(test_queue):
    """
    Test removing elements of the DeleteProtectedQueue.
    Should fail.

    :param DeleteProtectedQueue test_queue: The queue to verifiy.
    """

    with pytest.raises(TypeError):
        test_queue.get()
