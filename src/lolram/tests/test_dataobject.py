# encoding=utf8

'''Data object testing'''

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

import unittest
from lolram.dataobject import DataObject
from lolram import dataobject

class TestDataObject(unittest.TestCase):
	def test_getset(self):
		'''It should
		
		1. Return `None` for non-existing attribute
		2. Attribute should be same when getting and setting using both
			dot notation and `dict` notation
		'''
		
		do = DataObject()
		self.assertTrue(do.a is None)
		self.assertFalse(do.get('a'))
		do.a = 528491
		self.assertEqual(do['a'], 528491)
		self.assertEqual(do.a, 528491)
		do['b'] = 1122
		self.assertEqual(do['b'], 1122)
		self.assertEqual(do.b, 1122)
	
	def test_private_data(self):
		'''It should set and get attributes under `DataObject`.``__``'''
		
		do = DataObject()
		do.__.a = 528491
		self.assertEqual(do.__.a, 528491)
	
	def test_init_from_dict(self):
		'''It should support population from `dict` and keyword arguments
		on `DataObject` instantiation'''
		
		do = DataObject({'a':528491})
		self.assertEqual(do.a, 528491)
		
		do = DataObject(a=528491)
		self.assertEqual(do.a, 528491)
	
	def test_raise_key_error(self):
		'''It should accept ``__raises_key_error`` as a keyword argument
		and raise errors if keys are not found'''
		
		do = DataObject(__raises_key_error=True)
		self.assertRaises(KeyError, lambda:do.a)
	
	def test_special_funcs(self):
		do = DataObject()
		self.assertEqual(unicode(do), u'{}')
	
	
if __name__ == '__main__':
	unittest.main()

