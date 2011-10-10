# encoding=utf8

'''cms testing'''

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
import cStringIO

import pymongo

from lolram2.tests import config
from lolram2.cms.mongo import ManagerOnMongo
from lolram2.respool.mongo import TextResPoolOnMongo
from lolram2.respool.filesystem import FileResPoolOnFilesystem

class TestCMSOnMongo(unittest.TestCase):
	def setUp(self):
		self.connection = pymongo.Connection()
		self.database = self.connection.unittest
		self.database.authenticate(config.MONGO_USERNAME, config.MONGO_PASSWORD)
		text_res_pool = TextResPoolOnMongo()
		text_res_pool.set_mongo_collection(self.database.texts)
		file_res_pool = FileResPoolOnFilesystem()
		temp_dir = tempfile.mkdtemp()
		file_res_pool.set_file_dir(temp_dir)
		self.manager = ManagerOnMongo(self.database, text_res_pool, 
			file_res_pool)
	
	def tearDown(self):
		for name in self.database.collection_names():
			if name.startswith('system'):
				continue
			
			self.database.drop_collection(name)
	
	def test_text_revisions(self):
		'''It should save new articles with their revisions'''
		
		m = self.manager
		
		s1 = u'hello¶'
		s2 = u'⁓'
		
		article_version = m.new_article_version()
		article_version.text = s1
		
		m.save_article_version(article_version)
		
		article_uuid = article_version.article_uuid
		
		article_version = m.get_article_version(article_uuid=article_uuid)
		self.assertEqual(article_version.text, s1)
		
		article_version = m.get_article_version(article_uuid=article_uuid, 
			article_version_number=1)
		self.assertEqual(article_version.text, s1)
		
		article_version = m.new_article_version(article_uuid)
		article_version.text = s2
		
		m.save_article_version(article_version)
		
		article_version = m.get_article_version(article_uuid=article_uuid, 
			article_version_number=1)
		self.assertEqual(article_version.text, s1)
		
		article_version = m.get_article_version(article_uuid=article_uuid, 
			article_version_number=2)
		self.assertEqual(article_version.text, s2)
		
		article_version = m.get_article_version(article_uuid=article_uuid)
		self.assertEqual(article_version.text, s2)
	
	def test_file_revisions(self):
		'''It should save files'''
		
		m = self.manager

		f1 = cStringIO.StringIO('hello')
		
		article_version = m.new_article_version()
		article_version.file = f1
		
		m.save_article_version(article_version)
		
		article_version = m.get_article_version(article_uuid=
			article_version.article_uuid)
		
		self.assertEqual(article_version.file.read(), 'hello')
	
	def test_addresses(self):
		'''It should assign and remove addresses'''
		
		m = self.manager
		
		article_version = m.new_article_version()
		article_version.addresses = ['a', 'b']
		m.save_article_version(article_version)
		
		result = m.look_up_address('a')
		self.assertEqual(result, article_version.article_uuid)
		
		result = m.look_up_address('b')
		self.assertEqual(result, article_version.article_uuid)
		
		result = m.look_up_address('kitteh')
		self.assertFalse(result)
		
		article_version = m.new_article_version(article_version.article_uuid)
		article_version.addresses = ['a', 'c']
		m.save_article_version(article_version)
		
		result = m.look_up_address('a')
		self.assertEqual(result, article_version.article_uuid)
		
		result = m.look_up_address('b')
		self.assertFalse(result)
		
		result = m.look_up_address('c')
		self.assertEqual(result, article_version.article_uuid)
		
		result = m.look_up_address('kitteh')
		self.assertFalse(result)
		
		# Test conflict
		article_version = m.new_article_version()
		article_version.addresses = ['a']
		self.assertRaises(Exception, 
			lambda: m.save_article_version(article_version))
		
	def test_tree(self):
		'''It should assign articles in trees'''
		
		m = self.manager
		
		article_version = m.new_article_version()
		m.save_article_version(article_version)
		
		article_version2 = m.new_article_version()
		article_version2.parent_article_uuids = [article_version.article_uuid]
		m.save_article_version(article_version2)
		
		article_version3 = m.new_article_version()
		article_version3.parent_article_uuids = [article_version.article_uuid]
		m.save_article_version(article_version3)
		
		article_version4 = m.new_article_version()
		article_version4.parent_article_uuids = [article_version3.article_uuid]
		m.save_article_version(article_version4)
		
		article_version5 = m.new_article_version()
		article_version5.parent_article_uuids = [
			article_version4.article_uuid, 
			article_version3.article_uuid,
		]
		m.save_article_version(article_version5)
		
		results = m.browse_articles(parent_uuid=article_version.article_uuid)
		self.assertEqual(len(list(results)), 2)
		
		results = m.browse_articles(parent_uuid=article_version.article_uuid,
			descendants=True)
		self.assertEqual(len(list(results)), 4)