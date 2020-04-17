import logging
import os
import signal
import time

import RPi.GPIO as GPIO
import yaml

from berry_cam.threads.heartbeat import Heartbeat
from berry_cam.threads.image_capturing import ImageCapturing
from berry_cam.threads.settings_loader import SettingsLoader
from berry_cam.threads.uploader import Uploader

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

threads = []


def stop(signum=None, frame=None):
    """
    Will stop the camera. Parameters are required for signal handling.

    :param signum: The number of the raised signal
    :param frame: The current stack frame
    """
    logging.info("Stopping...")
    for curr_thread in threads:
        curr_thread.stop()


logging.info("Starting...")

# Init signal handling
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)

# Open config file
yaml_path = os.path.join(os.path.dirname(__file__), 'conf.yaml')
with open(yaml_path) as config_file:
    config = yaml.safe_load(config_file)

    # Init heartbeat thread to notify the server that the camera is up
    heartbeat = Heartbeat(
        config['camera']['name'],
        '{}/api/camera/'.format(config['image_server']['server_url']),
        config['image_server']['api_key'],
        config['image_server']['retry_count'])
    threads.append(heartbeat)

    # Init uploader thread that will upload new images
    uploader = Uploader(
        '{}/api/picture/'.format(config['image_server']['server_url']),
        config['image_server']['api_key'],
        config['image_server']['retry_count'])
    threads.append(uploader)

    # Check PIR config
    pin_number_type = None
    if config['pir']['number_type'] == "BCM":
        pin_number_type = GPIO.BCM
    elif config['pir']['number_type'] == "BOARD":
        pin_number_type = GPIO.BOARD
    else:
        logging.error("Invalid pir number type found. Can be either BOARD or BCM."
                      "Instead, found %s", config['pir']['number_type'])
        stop()

    # Init image capturing thread that will read out the camera
    image_capturing = ImageCapturing(
        pin_number_type,
        config['pir']['pin'],
        config['camera']['image_location'],
        config['pir']['reset_time'],
        uploader.upload_queue)
    threads.append(image_capturing)

    # Init settings refresh thread that will regularly fetch configuration from image server
    threads.append(
        SettingsLoader(
            config['camera']['name'],
            '{}/api/camera/'.format(config['image_server']['server_url']),
            config['image_server']['api_key'],
            config['image_server']['retry_count'],
            (heartbeat, image_capturing)))

    # Start the threads
    logging.info("Running...")
    for thread in threads:
        thread.start()

    # Wait until one thread is finished, then stop the others.
    while True:
        all_alive = True
        for thread in threads:
            if not thread.is_alive():
                all_alive = False

        if not all_alive:
            break

        time.sleep(0.5)

    stop()
    logging.info("Waiting for threads to stop...")
    while threads:
        thread = threads.pop()
        thread.join()
        logging.info("%s threads left...", len(threads))

logging.info("Finished")
