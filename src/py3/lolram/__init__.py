'''Python web framework and utilities

Lolram is a collection of Python web framework and utilities that powers 
www.torwuf.com.
'''
# This file is part of Lolram.
# Copyright © 2012 Christopher Foo <chris.foo@gmail.com>.
# Licensed under GNU GPLv3. See COPYING.txt for details.
import distutils.version

__docformat__ = 'restructuredtext en'
short_version = '0.1'  # N.N
__version__ = '0.1'  # N.N[.N]+[{a|b|c|rc}N[.N]+][.postN][.devN]
description, long_description = __doc__.split('\n', 1)
long_description = long_description.lstrip()

distutils.version.StrictVersion(__version__)
