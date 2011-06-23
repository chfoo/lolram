# encoding=utf8

'''App testing'''

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
import os.path
import gzip
import cStringIO
import wsgiref.util
import sys
import os
import httplib
import Cookie
import subprocess
import time

import server_base
from lolram import app

PRE_CHUNK = ['This is the data in the first chunk\r\n',
	'and this is the second one\r\n',
	'con', 'sequence']

POST_CHUNK = ['25', 'This is the data in the first chunk\r\n',
	'1C', 'and this is the second one\r\n', '3', 'con', '8', 'sequence',
	'0', '']

# utf-8 encoded
PRE_COMPRESS = 'Kittens!\n\tKittens!\n\xc3\xa4\xc3\xa5\xc3\xa9\xc3' \
	'\xab\xc3\xbe\xc3\xbc\xc3\xba\xc3\xad\xc3\xb3\xc3\xb6\xc2\xab\xc2' \
	'\xbb\xc3\xa1\xc3\x9f\xc3\xb0fgh\xc3\xaf\xc5\x93\xc3\xb8\xc2\xb6\xc3' \
	'\xa6\xc5\x93\xc2\xa9\xc2\xaeb\xc3\xb1\xc2\xb5\xc3\xa7\xc2\xa6\n\n\n' 

class TestApp(server_base.ServerBase, unittest.TestCase):
	def __init__(self, *args):
		server_base.ServerBase.__init__(self)
		unittest.TestCase.__init__(self, *args)
		
		confname = os.path.join(os.path.dirname(__file__), 'app.conf')
		self.start_server(confname)
		
		# XXX: wait until intialized
		time.sleep(0.25)
		
		response = self.request('/cleanup')
		self.assertEqual(response.status, 200)
		
	def setUp(self):
		server_base.ServerBase.setUp(self)
	
	def tearDown(self):
		server_base.ServerBase.tearDown(self)
		
	def test_basic(self):
		'''It should not crash'''
		response = self.request('/')
	
	def test_session_empty(self):
		'''It should not set cookie if there is no session data'''
		
		response = self.request('/session_test')
		self.assertEqual(response.status, 200)
		self.assertEqual(response.getheader('set-cookie'), None)
	
	def test_session_temp_to_permanent(self):
		'''It should set data, send cookie, and send another cookie if session
		is changed to permanent. It should retrieve saved session data'''
		
		response = self.request('/session_test;data?data=kittens')
		self.assertEqual(response.status, 200)
		
		cookieobj = Cookie.SimpleCookie()
		for key, value in response.getheaders():
			if key.lower() == 'set-cookie':
				cookieobj.load(value)
		self.assertTrue(cookieobj['lolramsidt'])
		
		response = self.request('/session_test;get',
			headers={'Cookie':'lolramsidt=%s' % cookieobj['lolramsidt']})
		self.assertEqual(response.status, 200)
		self.assertEqual(response.read(), 'kittens')
		
		response = self.request('/session_test;persist',
			headers={'Cookie':'lolramsidt=%s' % cookieobj['lolramsidt']})
		self.assertEqual(response.status, 200)
		
		for key, value in response.getheaders():
			if key.lower() == 'set-cookie':
				cookieobj.load(value)
		self.assertTrue(cookieobj['lolramsid'])
		
		response = self.request('/session_test;get',
			headers={'Cookie':'lolramsidt=%s' % cookieobj['lolramsidt']})
		self.assertEqual(response.status, 200)
		self.assertEqual(response.read(), 'kittens')
		
#		response = self.request('/session_test;get',
#			headers={'Cookie':'lolramsid=%s' % cookieobj['lolramsid']})
#		self.assertEqual(response.status, 200)
#		self.assertEqual(response.read(), 'kittens')

	def test_session_bad_cookie(self):
		'''It should not crash if bad cookie is sent to server'''
		
		response = self.request('/session_test;get',
			headers={'Cookie':'lolramsidt=garbage'})
		self.assertEqual(response.status, 200)
	
	def test_response_crash_status_code(self):
		'''It should crash and return status code 500 and not 200'''
		response = self.request('/crash_test')
		self.assertEqual(response.status, 500)
	
	def test_not_found(self):
		'''it should return 404 error if path does not exist'''
		response = self.request('/path_that_does_not_exist')
		self.assertEqual(response.status, 404)
	
	def test_wui_basic(self):
		'''It should return a page with a basic HTML structure'''
		response = self.request('/wui_basic_test')
		s = response.read()
		self.assertEqual(response.status, 200)
		self.assertTrue(s.index('html'))
		self.assertTrue(s.index('head'))
		self.assertTrue(s.index('body'))
		
	def test_static_file(self):
		'''It should return a file from the www directory'''
		
		response = self.request('/zf/test.txt')
		self.assertEqual(response.status, 200)
		self.assertTrue(response.read().startswith('Hello world'))
		
	def test_account_basic_password(self):
		'''It should accept our basic password'''
		
		response = self.request('/account_basic_test',
			query={'password':'cake'})
		self.assertEqual(response.status, 200)
		self.assertEqual(response.read(), 'ok')
		
	def test_account_basic_password_fail(self):
		'''It should reject our basic password'''
		
		response = self.request('/account_basic_test',
			query={'password':'fish-shaped candy'})
		self.assertEqual(response.status, 200)
		self.assertEqual(response.read(), 'fail')
	
	def test_text_pool(self):
		'''It should store and retrieve text'''
		
		text1 = u'Stochastic Ruby Dragon'
		text2 = u'Stochastic Ruby Dragon⁓'
		
		response = self.request('/res_pool_text_test',
			query={'action':'get', 'id': '8000000'})
		self.assertEqual(response.status, 200)
		self.assertEqual(response.read(), 'None')
		
		response = self.request('/res_pool_text_test',
			query={'action':'set', 'text': text1})
		self.assertEqual(response.status, 200)
		text1_id = response.read()
		
		response = self.request('/res_pool_text_test',
			query={'action':'get', 'id': text1_id})
		self.assertEqual(response.status, 200)
		self.assertEqual(response.read(), text1)
		
		response = self.request('/res_pool_text_test',
			query={'action':'set', 'text': text1})
		self.assertEqual(response.status, 200)
		self.assertEqual(response.read(), text1_id)

		response = self.request('/res_pool_text_test',
			query={'action':'set', 'text': text2})
		self.assertEqual(response.status, 200)
		text2_id = response.read()
		
		self.assertTrue(text2_id != text1_id)
	
	def test_file_pool(self):
		'''It should store and retrieve files'''
		
		text1 = u'Stochastic Ruby Dragon'.encode('utf8')
		text2 = u'Stochastic Ruby Dragon⁓'.encode('utf8')
		
		response = self.request('/res_pool_file_test',
			query={'action':'get', 'id': '8000000'})
		self.assertEqual(response.status, 200)
		self.assertEqual(response.read(), 'None')
		
		response = self.request('/res_pool_file_test',
			query={'action':'set'}, data={'file': ('filename.txt', text1)})
		self.assertEqual(response.status, 200)
		text1_id = response.read()
		
		response = self.request('/res_pool_file_test',
			query={'action':'get', 'id': text1_id})
		self.assertEqual(response.status, 200)
		self.assertEqual(response.read(), text1)
		
		response = self.request('/res_pool_file_test',
			query={'action':'set'}, data={'file': ('filename.txt', text1)})
		self.assertEqual(response.status, 200)
		self.assertEqual(response.read(), text1_id)

		response = self.request('/res_pool_file_test',
			query={'action':'set'}, data={'file': ('filename.txt', text2)})
		self.assertEqual(response.status, 200)
		text2_id = response.read()
		
		self.assertTrue(text2_id != text1_id)
		

class TestAppFuncs(unittest.TestCase):
	
	def test_chunked_transfer(self):
		'''It should format data into chunked transfer encoding'''
		
		self.assertEqual(''.join(app.chunked(PRE_CHUNK)), '\r\n'.join(POST_CHUNK))
	
	def test_compress(self):
		'''It should compress the data and the data should be the same 
		uncompressed'''
		
		n = 5
		l = (PRE_COMPRESS[i:i+n] for i in range(0, len(PRE_COMPRESS), n))
		gzip_file = gzip.GzipFile(fileobj=cStringIO.StringIO(
			''.join(app.compress(l))))
		result = gzip_file.read()
		self.assertEqual(result, PRE_COMPRESS)
		
class TestAppExecutable(unittest.TestCase):
	def test_simple(self):
		path_arg = os.path.abspath(
			os.path.join(os.path.dirname(__file__), '..', '..', 'lolram'))
		proc = subprocess.Popen(['env', 'python', path_arg])
		proc.terminate()
		self.assertFalse(proc.returncode)
