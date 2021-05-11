#!/usr/bin/python3

from setuptools import setup, find_packages


setup(
    name="OCARIOT",
    version="0.1",
    packages=find_packages(),
    scripts=['ocariot_demo.py', 'ocariot_backup.py'],

    install_requires=['smbus2', 'smbus-cffi', 'pn532pi'],

    # metadata to display on PyPI
    author="OCARIOT",
    description="OCARIOT Scale Demo",
    keywords="OCARIOT Scale Demo weight",
    url="https://ocariot.eu",
)
