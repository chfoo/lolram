# encoding=utf8

'''iterable utils testing'''

#	Copyright © 2011 Christopher Foo <chris.foo@gmail.com>

#	This file is part of Lolram.

#	Lolram is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.

#	Lolram is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.

#	You should have received a copy of the GNU General Public License
#	along with Lolram.  If not, see <http://www.gnu.org/licenses/>.

__docformat__ = 'restructuredtext en'

import unittest

from lolram2 import iterutils


class TestIterUtils(unittest.TestCase):
	def test_trigger(self):
		'''It should trigger an error that does not get evaluated immediately'''
		
		def my_fn(fn):
			fn()
			yield 1
			yield 2
			yield 3
		
		def my_bad_fn():
			return 1 / 0
		
		r = my_fn(my_bad_fn) # doesn't raise error!
		
		# force it to raise
		self.assertRaises(ZeroDivisionError, lambda:iterutils.trigger(r))
		
		