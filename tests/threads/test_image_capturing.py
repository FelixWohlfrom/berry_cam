# Replace python libraries with mocked ones.
# Needs to be done as first step before any other imports.
import sys
import fake_rpi

sys.modules['RPi'] = fake_rpi.RPi  # Fake RPi
sys.modules['RPi.GPIO'] = fake_rpi.RPi.GPIO  # Fake GPIO
sys.modules['picamera'] = fake_rpi.picamera  # Fake picamera

# Now add the real imports
import time

from queue import Queue
from testfixtures import LogCapture
from tempfile import TemporaryDirectory

from berry_cam.threads.image_capturing import ImageCapturing

from fake_rpi.RPi import GPIO

# The pin to use for testing
GPIO_PIN = 23


def test_stop_pir_not_ready():
    """
    Tests that the stopping the thread also works even if the PIR was not ready yet.
    """

    with LogCapture(names='berry_cam.threads.image_capturing') as log:
        with TemporaryDirectory() as tmpdir:
            GPIO.set_input(23, 1)  # PIR not ready yet
            image_capturing = ImageCapturing(GPIO.BCM, GPIO_PIN, tmpdir, 1, Queue())
            image_capturing.start()
            time.sleep(0.5)
            image_capturing.stop()
            image_capturing.join(0.5)

            log.check_present(
                ('berry_cam.threads.image_capturing', 'DEBUG',
                 'Thread stopped while camera was not ready yet. Stopping.')
            )
            assert not image_capturing.is_alive()


def test_stop_pir_ready_not_enabled():
    """
    Tests that stopping the thread also works if the PIR signalled to be ready,
    but the camera was not enabled yet.
    """

    with LogCapture(names='berry_cam.threads.image_capturing') as log:
        with TemporaryDirectory() as tmpdir:
            GPIO.set_input(23, 0)
            image_capturing = ImageCapturing(GPIO.BCM, GPIO_PIN, tmpdir, 1, Queue())
            image_capturing.start()
            time.sleep(0.5)
            image_capturing.stop()
            image_capturing.join(1)

            log.check_present(
                ('berry_cam.threads.image_capturing', 'INFO', 'Ready...')
            )
            assert not image_capturing.is_alive()


def test_enabled_no_movement():
    """
    Verifies that the thread behaves correctly if the camera is enabled,
    but no movement is recognized.
    """

    with LogCapture(names='berry_cam.threads.image_capturing') as log:
        with TemporaryDirectory() as tmpdir:
            GPIO.set_input(23, 0)
            image_capturing = ImageCapturing(GPIO.BCM, GPIO_PIN, tmpdir, 1, Queue())
            image_capturing.start()
            image_capturing.enabled = True
            time.sleep(0.5)
            image_capturing.stop()
            image_capturing.join(1)

            log.check_present(
                ('berry_cam.threads.image_capturing', 'INFO', 'Ready...')
            )
            assert not image_capturing.is_alive()


def test_enabled_with_movement():
    """
    Verifies that images are properly captured if movement is detected.
    """

    with LogCapture(names='berry_cam.threads.image_capturing') as log:
        with TemporaryDirectory() as tmpdir:
            GPIO.set_input(23, 0)
            upload_queue = Queue()
            reset_time = 1  # Reset time of PIR in seconds
            image_capturing = ImageCapturing(GPIO.BCM, GPIO_PIN, tmpdir, reset_time, upload_queue)
            image_capturing.start()
            image_capturing.enabled = True
            time.sleep(0.5)
            GPIO.set_input(23, 1)  # Movement detected
            time.sleep(1)
            GPIO.set_input(23, 0)  # Movement stopped
            time.sleep(0.5)
            image_capturing.stop()
            image_capturing.join(reset_time + 1)

            log.check_present(
                ('berry_cam.threads.image_capturing', 'INFO', 'Ready...'),
                ('berry_cam.threads.image_capturing', 'INFO', 'Movement recognized, taking pictures.'),
                ('berry_cam.threads.image_capturing', 'INFO', 'No more movement, stop capturing.')
            )
            # We expect 1 or 2 images to be taken, depending on timings
            assert upload_queue.qsize() in [1, 2]
            assert not image_capturing.is_alive()
