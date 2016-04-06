from setuptools import setup, find_packages
from setup_util import write_version_module

VERSION = '0.2.0'

write_version_module(VERSION, 'vcl/version.py')

setup(
    name='virtual-cluster-libs',
    version=VERSION,
    packages=find_packages(),
    entry_points={'console_scripts': [
        'vcl = vcl.__main__:main',
    ]},
    license='Apache 2.0',
)
