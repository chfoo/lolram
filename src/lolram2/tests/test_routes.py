# encoding=utf8

'''Routing testing'''

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

from lolram2 import routes

class TestRoutes(unittest.TestCase):
	def test_route(self):
		'''
		1. It should return `None` if not found.
		2. It should have the same behaviour on leading slash and on no 
			leading slash
		3. It should have the same behaviour likewise for trailing slashes.
		4. It should return a default value if not found
		5. It should accept a default value and use that given value if not found
		6. It should be matching for URL paths only
		7. It should accept more specific paths first (ie, greater depths)
		'''
		
		router = routes.Router()
		self.assertTrue(router.get('dummy') is None)
		router.set('aabb', 'aabb_data')
		router.set('/ccdd/', 'ccdd_data')
		router.set('eeff/gghh', 'eeffgghh_data')
		router.set('/', 'dcccc')
		router.set('/a/', 'a')
		router.set('/a/b/c/d', 'abcd')
		router.set('/a/b/', 'ab')
		self.assertEqual(router.get('aabb'), 'aabb_data')
		self.assertEqual(router.get('aabb;asdf?dd=rr'), 'aabb_data')
		self.assertEqual(router.get('/aabb'), 'aabb_data')
		self.assertEqual(router.get('ccdd/'), 'ccdd_data')
		self.assertEqual(router.get('eeff/gghh'), 'eeffgghh_data')
		self.assertEqual(router.get('/eeff/gghh'), 'eeffgghh_data')
		self.assertEqual(router.get('/'), 'dcccc')
		self.assertEqual(router.get(''), 'dcccc')
		self.assertEqual(router.get('a'), 'a')
		self.assertEqual(router.get('a/b'), 'ab')
		self.assertEqual(router.get('a/b/c/d'), 'abcd')
		self.assertTrue(router.get('dummy') is None)
		router.set_default('5fjfj')
		self.assertEqual(router.get('dummy', default=528491), 528491)
		self.assertEqual(router.get('dummy'), '5fjfj')
	
