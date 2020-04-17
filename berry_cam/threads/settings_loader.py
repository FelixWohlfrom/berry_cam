import json
import logging
import time
from http import HTTPStatus
from threading import Thread

import requests

LOG = logging.getLogger(__name__)


class SettingsLoader(Thread):
    """
    This thread regularly checks on image server for settings updates (e.g. camera enabling).
    """

    def __init__(self, name, url, api_key, retry_count, enabled_updater=None):
        """
        Creates a new settings loader thread

        :param name: The name of the camera to read the settings for.
        :param url: The url to read the data from.
        :param api_key: The api key to authenticate at the server.
        :param retry_count: Retry this often if connection fails.
        :param enabled_updater: A list of elements to update 'enabled' property on changes.
        """

        super().__init__()
        self._name = name
        self._url = url
        self._api_key = api_key
        self._retry_count = retry_count

        if enabled_updater:
            self.enabled_updater = enabled_updater
        else:
            self.enabled_updater = []

        self._run_settings_loader = True

    def stop(self):
        """
        Signals this thread to stop as soon as possible.
        """
        self._run_settings_loader = False

    def run(self):
        """
        Runs the thread.
        """
        LOG.info("Settings loader started...")
        while self._run_settings_loader:
            try_count = 0
            for try_count in range(self._retry_count):
                if not self._run_settings_loader:
                    break

                try:
                    # Try to read settings from server
                    response = requests.get(self._url,
                                            params={'name': self._name,
                                                    'api_key': self._api_key})
                    if response.status_code == HTTPStatus.FORBIDDEN:
                        LOG.error(
                            "Settings loader: Access denied. Please check your api key.")
                        return

                    # Try to read enabled state from settings and update elements with read state
                    new_enabled = response.json().get('enabled', False)
                    LOG.debug("Settings loader: Read setting 'enabled': %s", new_enabled)
                    for entry in self.enabled_updater:
                        entry.enabled = new_enabled

                    break

                except (requests.exceptions.ConnectionError, json.decoder.JSONDecodeError) as error:
                    LOG.error(
                        "Settings loader: Error while connecting to server. Retrying...")
                    LOG.error(error)
                    time.sleep(1)

            # Retries exceeded, stop uploader
            if try_count == self._retry_count - 1:
                LOG.error("Settings loader: Failed to get settings after %s tries, giving up. "
                          "Are you sure the server is up?", self._retry_count)
                self._run_settings_loader = False
                return

            # Wait until next iteration
            for _ in range(10):
                time.sleep(1)
                if not self._run_settings_loader:
                    break
