from distutils.core import setup
import sys
import os

assert sys.version_info[0] == 3

with open('VERSION') as f:
    __version__ = f.read().strip()


setup(
    name='torwuf',
    version=__version__,
    author='Christopher Foo',
    author_email='chris.foo@gmail.com',
    packages=[
        'torwuf',
        'torwuf.controllers',
        'torwuf.models',
        'torwuf.views',
    ],
    requires=[
        'tornado(>=2.4.1)',
        'docutils',
        'pymongo',
        'pywheel',
        'isodate',
    ],
    package_dir={
        'torwuf': 'src/py3/torwuf',
    },
    package_data={
        'torwuf.views': [
            'resources/*.*[!~]',
            'resources/*/*.*[!~]',
            'resources/*/*/*.*[!~]',
            'templates/*.*[!~]',
            'templates/*/*.*[!~]',
            'templates/*/*/*.*[!~]',
        ],
    }
)

