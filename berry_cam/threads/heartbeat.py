import logging
import time
from http import HTTPStatus
from threading import Thread

import requests

LOG = logging.getLogger(__name__)


class Heartbeat(Thread):
    """
    A heartbeat thread. Will regularly send 'alive' information to the image server.
    """

    def __init__(self, name, url, api_key, retry_count):
        """
        Creates a new heartbeat thread.

        :param name: The name of the current camera.
        :param url: The url to send the heartbeat to
        :param api_key: The api key for authentication
        :param retry_count: How often sending should be retried before failing.
        """
        super().__init__()
        self._name = name
        self._url = url
        self._api_key = api_key
        self._retry_count = retry_count

        self.enabled = False  # Will be updated by settings loader

        self._run_heartbeat = True

    def stop(self):
        """
        Signals this thread to stop as soon as possible.
        """
        self._run_heartbeat = False

    def run(self):
        """
        Runs the thread.
        """
        LOG.info("Heartbeat started...")
        while self._run_heartbeat:
            LOG.info("Heartbeat sending...")
            try_count = 0
            for try_count in range(self._retry_count):
                if not self._run_heartbeat:
                    break

                try:
                    response = requests.post(self._url,
                                             data={'name': self._name,
                                                   'api_key': self._api_key,
                                                   'enabled': self.enabled})
                    if response.status_code == HTTPStatus.OK:
                        LOG.debug("Heartbeat sent.")

                    if response.status_code == HTTPStatus.FORBIDDEN:
                        LOG.error(
                            "Heartbeat: Access denied. Please check your api key.")
                        return

                    break

                except requests.exceptions.ConnectionError as error:
                    LOG.error(
                        "Heartbeat: Error while connecting to server. Retrying...")
                    LOG.error(error)
                    time.sleep(1)

            # Retries exceeded, stop uploader
            if try_count == self._retry_count - 1:
                LOG.error("Heartbeat: Failed to send heartbeat after %s tries, giving up. "
                          "Are you sure the server is up?", self._retry_count)
                self._run_heartbeat = False
                return

            # Wait until next iteration
            for _ in range(30):
                time.sleep(1)
                if not self._run_heartbeat:
                    break
