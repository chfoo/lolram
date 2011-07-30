# encoding=utf8

'''respool testing'''

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
import random
import tempfile
import shutil
import cStringIO
import os.path

import pymongo

from lolram2.respool.mongo import TextResPoolOnMongo
from lolram2.respool.filesystem import FileResPoolOnFilesystem
from lolram2.tests import config

class TestResPoolOnMongo(unittest.TestCase):
	def setUp(self):
		self.connection = pymongo.Connection()
		self.database = self.connection.unittest
		self.database.authenticate(config.MONGO_USERNAME, config.MONGO_PASSWORD)
		self.collection = self.database['unittest_%s' % random.random()]
	
	def tearDown(self):
		self.collection.drop()
	
	def test_text(self):
		res = TextResPoolOnMongo()
		res.set_mongo_collection(self.collection)
		
		t1 = u'hello'
		t2 = u'stochastic ruby dragon·'
		
		n = res.set_text(t1)
		n2 = res.set_text(t2)
		n3 = res.set_text(t1)
		
		self.assertEqual(res.get_text(n), t1)
		self.assertEqual(res.get_text(n2), t2)
		self.assertEqual(res.get_text(n3), t1)
		self.assertEqual(n, n3)
		
class TestResPoolOnFilesystem(unittest.TestCase):
	def setUp(self):
		self.dir = os.path.join(tempfile.gettempdir(), 'unittest_%s' % random.random())
	
	def tearDown(self):
		if os.path.exists(self.dir):
			shutil.rmtree(self.dir)
	
	def test_file(self):
		res = FileResPoolOnFilesystem()
		res.set_file_dir(self.dir)
		
		f1 = cStringIO.StringIO('hello')
		f2 = cStringIO.StringIO('hello world')
		
		n = res.set_file(f1)
		n2 = res.set_file(f2)
		
		f1.seek(0)
		n3 = res.set_file(f1)
		
		self.assertEqual(res.get_file(n).read(), 'hello')
		self.assertEqual(res.get_file(n2).read(), 'hello world')
		self.assertEqual(res.get_file(n3).read(), 'hello')
		self.assertEqual(n, n3)