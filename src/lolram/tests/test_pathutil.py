# encoding=utf8

'''Path utility function testing'''

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

from lolram import pathutil

class TestPathUtil(unittest.TestCase):
	def test_common_empty(self):
		self.assertEqual(pathutil.common('', ''), ('', '', ''))
	
	def test_common_empty_one(self):
		self.assertEqual(pathutil.common('', 'b'), ('', '', 'b'))
		self.assertEqual(pathutil.common('a/a', ''), ('', 'a/a', ''))
	
	def test_common(self):
		self.assertEqual(pathutil.common('a', 'a'), ('a', '', ''))
		self.assertEqual(pathutil.common('a/1', 'a'), ('a', '1', ''))	
		self.assertEqual(pathutil.common('a', 'a/2/3'), ('a', '', '2/3'))
		self.assertEqual(pathutil.common('a/b/c', 'a/b/r/g'), ('a/b', 'c', 'r/g'))
	
	def test_common_leading_trailing_slashes(self):
		self.assertEqual(pathutil.common('/a', 'a'), ('a', '', ''))
		self.assertEqual(pathutil.common('a/', 'a'), ('a', '', ''))
		self.assertEqual(pathutil.common('a/b/c/', '/a/b'), ('a/b', 'c/', ''))
	
	
	
	
