from distutils.core import setup

common_packages = [
    'pyyaml', 'requests'
]

setup(
    name='berry_cam',
    version='0.1',
    description='A tool for raspberry pi to automatically capture pictures via a camera. Motion detection is done'
                'via PIR sensor. Images are directly uploaded to a server.',
    author='Felix Wohlfrom',
    author_email='FelixWohlfrom@users.noreply.github.com',
    packages=['berry_cam'],
    install_requires=common_packages,
    extras_require={
        # TODO: Add this dynamically if on raspi
        'raspi': [
            'RPi.GPIO',
            'picamera'
        ],
        'test': [
            'pytest', 'coverage', 'fake_rpi', 'testfixtures', 'requests-mock'
        ]
    }
)
