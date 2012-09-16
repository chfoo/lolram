#!/usr/bin/env python3

import os
import sys
from distutils.core import setup

src_dir = os.path.abspath(os.path.join('src', 'py3'))
sys.path.insert(0, src_dir)

import lolram

setup(name='lolram',
    version=lolram.__version__,
    description=lolram.description,
    long_description=lolram.long_description,
    author='Christopher Foo',
    author_email='chris.foo@gmail.com',
    url='https://launchpad.net/lolram',
    packages=['lolram', 
        'lolram.deprecated',
        'lolram.deprecated.tests',
        'lolram.deprecated.web',
        'lolram.deprecated.web.framework',
        'lolram.tornadol',
    ],
    package_dir={'': 'src/py3'},
    package_data={
    },
    classifiers=[
    ],
    requires=[],
)
