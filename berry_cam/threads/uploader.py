
import logging
import time
from http import HTTPStatus
from queue import Queue, Empty
from threading import Thread

import requests

LOG = logging.getLogger(__name__)


class DeleteProtectedQueue:
    """
    A queue to only add or read elements, but not remove them.
    """

    def __init__(self, queue):
        """
        Creates a new delete protected queue from given queue.
        Due to implementation restrictions, all modifications in the
        delete protected queue are also directly done in given queue.

        :param queue: The queue to delete protect.
        """
        self._queue = queue

    def __getattr__(self, name):
        """
        Returns a 'getter' of the queue. Only getters that do not modify the queue will return
        a valid attribute.

        :param name: The name of the attribute
        :return: The value of the queue function 'name'
        """
        if name != 'get' and name != 'get_nowait':
            return getattr(self._queue, name)
        return None


class Uploader(Thread):
    """
    This thread will upload images put into upload_queue to an image server.
    """

    def __init__(self, url, api_key, retry_count):
        """
        Creates a new uploader thread.

        :param url: The url to upload the images
        :param api_key: The api key to authenticate at the server
        :param retry_count: The amount of retries to upload before failing
        """
        super().__init__()
        self._url = url
        self._api_key = api_key
        self._retry_count = retry_count

        self._upload_queue = Queue()
        self._run_uploader = True

    @property
    def upload_queue(self):
        """
        Returns the upload queue.

        :return: A queue to which only new elements can be added, but not deleted.
        """
        return DeleteProtectedQueue(self._upload_queue)

    def stop(self):
        """
        Signals this thread to stop as soon as possible.
        """
        self._run_uploader = False

    def run(self):
        """
        Runs the thread.
        """
        LOG.info("Uploader started...")
        while self._run_uploader:
            try:
                picture = self._upload_queue.get(True, 0.5)

                LOG.info("Uploading picture %s", picture)
                try_count = 0
                for try_count in range(self._retry_count):
                    if not self._run_uploader:
                        break

                    picture_data = {
                        'file': (picture, open(picture, 'rb'), 'image/jpeg')
                    }
                    try:
                        response = requests.post(self._url,
                                                 data={
                                                     'api_key': self._api_key},
                                                 files=picture_data)
                        if response.status_code == HTTPStatus.FORBIDDEN:
                            LOG.error(
                                "Uploader: Access denied. Please check your api key.")
                            return

                        if response.status_code == HTTPStatus.OK:
                            LOG.info(
                                "Upload succeeded after %s tries", try_count)
                            break  # Wait for the next picture

                        if 'message' in response.json():
                            LOG.error("Upload failed. Status code: %s, message: %s",
                                      response.status_code, response.json()['message'])
                            if 'errors' in response.json():
                                LOG.error(response.json()['errors'])
                        else:
                            LOG.error("Upload failed. Status code: %s, message: %s",
                                      response.status_code, response.content)

                    except requests.exceptions.ConnectionError as error:
                        LOG.error(
                            "Uploader: Error while connecting to server. Retrying...")
                        LOG.error(error)
                        time.sleep(1)

                # Retries exceeded, stop uploader
                if try_count == self._retry_count - 1:
                    LOG.error("Uploader: Failed to upload file after %s tries, giving up. "
                              "Are you sure the server is up?", self._retry_count)
                    return

            # If the queue is still empty, ignore it. Then check if we should stop the thread and
            # try to fetch images from queue again.
            except Empty:
                pass
