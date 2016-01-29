from setuptools import setup, find_packages
from setup_util import write_version_module

VERSION = '0.1.0'

write_version_module(VERSION, 'vcl/version.py')

setup(
    name='virtual-cluster-libs',
    version=VERSION,
    packages=find_packages(),
    license='Apache 2.0',
)
