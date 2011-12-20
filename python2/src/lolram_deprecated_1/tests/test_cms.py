# encoding=utf8

'''CMS component testing'''

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

import os.path
import server_base
import unittest

class TestApp(server_base.ServerBase, unittest.TestCase):
	def __init__(self, *args):
		server_base.ServerBase.__init__(self)
		unittest.TestCase.__init__(self, *args)
		
		confname = os.path.join(os.path.dirname(__file__), 'app.conf')
		self.start_server(confname)
	
	def tearDown(self):
		server_base.ServerBase.tearDown(self)
		response = self.request('/cleanup')
		self.assertEqual(response.status, 200)
		
	def test_article_text(self):
		'''It should create a new text article and be able to edit it'''
		
		text1 = 'stochastic ruby dragon.'
		text2 = 'kittens'
		
		response = self.request('/article_text_test', 
			query={'action':'new', 'text': text1})
		text1_id = int(response.read())
		
		response = self.request('/article_text_test', 
			query={'action':'get','id': str(text1_id)})
		self.assertEqual(response.read(), text1)
		
		response = self.request('/article_text_test', 
			query={'action':'edit','id': str(text1_id), 'text':text2})
		self.assertEqual(response.status, 200)
			
		response = self.request('/article_text_test', 
			query={'action':'get','id': str(text1_id)})
		self.assertEqual(response.read(), text2)
		
		response = self.request('/article_text_test', 
			query={'action':'revision','id': str(text1_id),
				'revision': str(0)})
		self.assertEqual(response.read(), text1)
		
		response = self.request('/article_text_test', 
			query={'action':'revision','id': str(text1_id),
				'revision': str(1)})
		self.assertEqual(response.read(), text2)
	
	def test_article_file(self):
		'''It should create new file article and be able to upload new versions'''
		
		text1 = 'Stochastic Ruby Dragon'
		text2 = 'stochastic ruby dragon'
		
		# Make a new one
		response = self.request('/article_file_test', 
			query={'action':'new'}, data={'file': ('test_file.txt', text1)})
		text1_id = int(response.read())
		
		# Get
		response = self.request('/article_file_test', 
			query={'action':'get', 'id': text1_id})
		self.assertEqual(response.read(), text1)
		
		# New revision
		response = self.request('/article_file_test', 
			query={'action':'edit', 'id': text1_id}, 
			data={'file': ('test_file2.txt', text2)})
		self.assertEqual(response.status, 200)
		
		# Get
		response = self.request('/article_file_test', 
			query={'action':'get', 'id': text1_id})
		self.assertEqual(response.read(), text2)
	
	def test_addresses(self):
		'''It should set and get addresses'''
		
		address1 = 'kitteh'
		address2 = 'kitten'
		address3 = 'doggeh'
		article_id = '19395'
		
		# Non-existent
		response = self.request('/address_test', 
			query={'action':'get', 'address':'asdfasdf'})
		self.assertEqual(response.read(), 'not found')
		
		
		response = self.request('/article_text_test', 
			query={'action':'new', 'text': 'asdf'})
		article_id = response.read()
		
		# Make new one
		response = self.request('/address_test', 
			query={'action':'set', 'address': address1, 'id': article_id})
		self.assertEqual(response.status, 200)
		
		response = self.request('/address_test', 
			query={'action':'get', 'address':address1})
		self.assertEqual(response.read(), article_id)
		
		# Make another
		response = self.request('/address_test', 
			query={'action':'set', 'address': address2, 'id': article_id})
		self.assertEqual(response.status, 200)
		
		response = self.request('/address_test', 
			query={'action':'get', 'address':address2})
		self.assertEqual(response.read(), article_id)
		
		# Delete one
		response = self.request('/address_test', 
			query={'action':'delete', 'address':address1})
		self.assertEqual(response.status, 200)
		
		response = self.request('/address_test', 
			query={'action':'get', 'address':address1})
		self.assertEqual(response.read(), 'not found')
		
		response = self.request('/address_test', 
			query={'action':'get', 'address':address2})
		self.assertEqual(response.read(), article_id)
		
		response = self.request('/article_text_test', 
			query={'action':'new', 'text': 'asdf'})
		article_id_2 = response.read()
		
		self.assertTrue(article_id != article_id_2)
		
		response = self.request('/address_test', 
			query={'action':'set', 'address': address3, 'id': article_id_2})
		self.assertEqual(response.status, 200)
		
		response = self.request('/address_test', 
			query={'action':'get', 'address':address2})
		self.assertEqual(response.read(), article_id)
		
		
	def test_article_tree(self):
		'''It should build article tree'''
		
		text1 = 'abc'
		text2 = 'def'
		
		response = self.request('/article_text_test', 
			query={'action':'new', 'text': text1})
		text1_id = response.read()
		
		response = self.request('/article_text_test', 
			query={'action':'new', 'text': text2})
		text2_id = response.read()
		
		response = self.request('/article_tree_test', 
			query={'action':'set', 'id': text1_id, 'child' : text2_id})
		self.assertEqual(response.status, 200)
		
		response = self.request('/article_tree_test', 
			query={'action':'get', 'id': text1_id})
		self.assertEqual(response.read(), text2_id)
	
		response = self.request('/article_tree_test', 
			query={'action':'delete', 'id': text1_id, 'child':text2_id})
		self.assertEqual(response.status, 200)
		
		response = self.request('/article_tree_test', 
			query={'action':'get', 'id': text1_id})
		self.assertEqual(response.read(), 'not found')
		
		
		
