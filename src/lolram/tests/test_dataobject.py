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
	
	def test_header_name(self):
		'''It should normalize strings to HTTP header names.
		
		Example::
			Http-Header-Name
		
		'''
		
		self.assertEqual(dataobject.normalize_header_name('ABC_DEF'), 'Abc-Def')
	
	def test_headers(self):
		'''It should
		
		1. Support `dict` notation. On assignment, it should replace 
			all headers with the
			same key name. On getting, it should retrieve the first header
			with the same key name.
		2. Key name should not be case-sensitive
		'''
		
		headers = dataobject.HTTPHeaders()
		headers['content_type'] = 'text/plain'
		for k in headers:
			self.assertEqual(k, 'Content-Type')
		self.assertEqual(headers['content_type'], 'text/plain')
		self.assertEqual(headers['content-type'], 'text/plain')
		self.assertEqual(headers['Content-Type'], 'text/plain')
		headers['Content-Type'] = 'text/html'
		self.assertEqual(headers['content_type'], 'text/html')
		headers.add('aa', 'bb', b_c='dbe', eeE_f='ddd')
		self.assertEqual(headers['aa'], 'bb; b-c=dbe; eeE-f=ddd')
	
	def test_headers2(self):
		'''It should support adding multiple headers with the same name.
		It should not overwrite using the ``add`` function'''
		
		headers = dataobject.HTTPHeaders()
		headers.add('set-cookie', 'asdf=123')
		headers.add('set-cookie', 'qwer=456')
		self.assertEqual(str(headers), 'Set-Cookie: asdf=123\n\r'
			'Set-Cookie: qwer=456\n\r')
		self.assertEqual(headers.items(), [
			('Set-Cookie', 'asdf=123'),
			('Set-Cookie', 'qwer=456'),
		])
	
	def test_headers_read_only(self):
		'''It should raise error if read-only is set'''
		
		headers = dataobject.HTTPHeaders()
		headers.add('set-cookie', 'asdf=123')
		
		headers.read_only = True
		
		self.assertRaises(AttributeError, 
			lambda: headers.add('set-cookie', 'def=345'))
		
		def f():
			headers['set-cookie'] = 'def=345'
		
		self.assertRaises(AttributeError, f)
		
		def f():
			del headers['set-cookie']
		
		self.assertRaises(AttributeError, f)

if __name__ == '__main__':
	unittest.main()

