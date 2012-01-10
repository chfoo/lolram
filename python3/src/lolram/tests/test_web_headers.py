'''WSGI Header testing'''
#
#	Copyright © 2011 Christopher Foo <chris.foo@gmail.com>
#
#	This file is part of Lolram.
#
#	Lolram is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	Lolram is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with Lolram.  If not, see <http://www.gnu.org/licenses/>.
#
import lolram.web.headers
import unittest

WSGI_HEADER_LIST = [
	('X-Kittens', 'Furry'),
	('Content-Type', 'text/plain; encoding=utf-8'),
	('X-Kittens', 'Fluffy'),
	('X-Kittens', 'Fuzzy'),
]

WSGI_HEADER_DICT = {
	'X-Kittens': ['Furry', 'Fluffy', 'Fuzzy'],
	'Content-Type': ['text/plain; encoding=utf-8'],
}

class TestHeaders(unittest.TestCase):
	def test_header_list_to_dict(self):
		'''It should convert a header list to a dict'''
		
		result = lolram.web.headers.header_list_to_dict(WSGI_HEADER_LIST)
		self.assertEqual(WSGI_HEADER_DICT, result)

	def test_header_dict_to_list(self):
		'''it should convert a header dict to a list'''
		
		result = lolram.web.headers.header_dict_to_list(WSGI_HEADER_DICT)
		self.assertEqual(sorted(WSGI_HEADER_LIST), sorted(result))

	def test_header_dict_mapping_to_list(self):
		'''it should convert a header dict to a list'''
		
		result = lolram.web.headers.HeaderListMap(WSGI_HEADER_LIST).to_list()
		self.assertEqual(sorted(WSGI_HEADER_LIST), sorted(result))
	

if __name__ == "__main__":
	#import sys;sys.argv = ['', 'Test.testName']
	unittest.main()