# encoding=utf8

'''HTTP header testing'''

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
from lolram2 import httpheaders

class TestDataObject(unittest.TestCase):
	def test_header_name(self):
		'''It should normalize strings to HTTP header names.
		
		Example::
			Http-Header-Name
		
		'''
		
		self.assertEqual(httpheaders.normalize_header_name('ABC_DEF'), 'Abc-Def')
	
	def test_headers(self):
		'''It should
		
		1. Support `dict` notation. On assignment, it should replace 
			all headers with the
			same key name. On getting, it should retrieve the first header
			with the same key name.
		2. Key name should not be case-sensitive
		'''
		
		headers = httpheaders.HTTPHeaders()
		headers['content_type'] = 'text/plain'
		for k in headers:
			self.assertEqual(k, 'Content-Type')
		self.assertEqual(headers['content_type'], 'text/plain')
		self.assertEqual(headers['content-type'], 'text/plain')
		self.assertEqual(headers['Content-Type'], 'text/plain')
		headers['Content-Type'] = 'text/html'
		self.assertEqual(headers['content_type'], 'text/html')
		headers.add_header('aa', 'bb', b_c='dbe', eeE_f='ddd')
		self.assertEqual(headers['aa'], 'bb; b-c=dbe; eeE-f=ddd')
	
	def test_headers2(self):
		'''It should support adding multiple headers with the same name.
		It should not overwrite using the ``add`` function'''
		
		headers = httpheaders.HTTPHeaders()
		headers.add_header('set-cookie', 'asdf=123')
		headers.add_header('set-cookie', 'qwer=456')
		self.assertEqual(str(headers), 'Set-Cookie: asdf=123\n\r'
			'Set-Cookie: qwer=456\n\r')
		self.assertEqual(headers.items(), [
			('Set-Cookie', 'asdf=123'),
			('Set-Cookie', 'qwer=456'),
		])
	
