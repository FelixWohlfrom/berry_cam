import logging
import os
import time
from threading import Thread

import RPi.GPIO as GPIO
from picamera import PiCamera

LOG = logging.getLogger(__name__)


class ImageCapturing(Thread):
    """
    The image capturing thread. Will capture the image from raspi if PIR signals motion and put captured image
    into an upload queue.
    """

    def __init__(self, port_type, pin, image_location, reset_time, upload_queue):
        """
        Creates a new image capturing thread.

        :param port_type: The type of port counting (GPIO.BCM or GPIO.BOARD)
        :param pin: The pin on which the PIR is connected.
        :param image_location: The location where the images should be stored.
        :param reset_time: Reset time after which the PIR is able to detect motion again.
        :param upload_queue: New images will be stored in this queue and can e.g. be processed in another thread.
        """
        super().__init__()

        self._image_location = image_location
        self._reset_time = reset_time
        self._GPIO_PIR = pin
        self._upload_queue = upload_queue

        # Set pin as input
        GPIO.setmode(port_type)
        GPIO.setup(self._GPIO_PIR, GPIO.IN)

        self.enabled = False  # Will be updated by settings loader

        self._run_camera = True

    def stop(self):
        """
        Signals this thread to stop as soon as possible.
        """
        self._run_camera = False

    def run(self):
        """
        Runs the thread.
        """
        LOG.info("Image capturing started...")
        LOG.info("Wait for PIR to be in sleep state ...")
        while self._run_camera and GPIO.input(self._GPIO_PIR) != 0:
            time.sleep(0.1)

        if not self._run_camera:
            LOG.debug("Thread stopped while camera was not ready yet. Stopping.")
            return

        LOG.info("Ready...")

        last_state = 0

        # Load camera with resolution of 1024x768 to save some space.
        with PiCamera(resolution=(1024, 768)) as camera:
            while self._run_camera:
                if self.enabled:
                    # Read pir state
                    pir_state = GPIO.input(self._GPIO_PIR)

                    # If motion is recognized, capture a picture and store it in upload queue
                    if pir_state == 1:
                        image_path = os.path.join(
                            self._image_location, '{}.jpg'.format(time.time()))
                        camera.capture(image_path)
                        self._upload_queue.put(image_path)

                    # Only print the info msg on raising flank for pir state = switch from non motion to motion
                    if pir_state == 1 and last_state == 0:
                        LOG.info("Movement recognized, taking pictures.")
                        last_state = 1

                    # The PIR needs ~5 seconds until it is ready again, so wait some time on a falling flank.
                    elif pir_state == 0 and last_state == 1:
                        LOG.info("No more movement, stop capturing.")
                        time.sleep(self._reset_time)
                        LOG.info("Ready...")
                        last_state = 0

                # Sleep some time until next check
                time.sleep(0.5)
