# encoding=utf8

'''URL N11n testing'''

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

from lolram.urln11n import URL
from lolram import urln11n 

__docformat__ = 'restructuredtext en'

class TestURL(unittest.TestCase):
#	def test_parse_mailto(self):
#		s = 'mailto:user@example.com'
#		url = URL(s)
#		self.assertEqual(url.scheme, 'mailto')
#		self.assertEqual(url.username, 'user')
#		self.assertEqual(url.hostname, 'example.com')
#		self.assertEqual(str(url), s)
	
	def test_parse_http(self):
		'''It should accept a URL and unescape each part. It should
		support queries with multiple keys with the same name.'''
		
		s = 'http://user:password@example.com:8080/' \
			'~justin/kittens%C2%A4;a' \
			'?q=b&q=a&e&b=%C3%A4%C3%A5%C3%A9%C3%AB%C3%BE%C3%BC%C3%BA%C3%AD' \
			'%C3%B3%C3%B6%C3%A1%C3%9F%C3%B0fgh%C3%AF%C5%93%C3%B8%C3%A6%C5' \
			'%93%C2%A9%C2%AEb%C3%B1&q=c&d=f#s'
		
		url = URL(s)
		self.assertEqual(url.scheme, 'http')
		self.assertEqual(url.username, 'user')
		self.assertEqual(url.password, 'password')
		self.assertEqual(url.hostname, 'example.com')
		self.assertEqual(url.port, 8080)
		self.assertEqual(url.path, u'~justin/kittens¤')
		self.assertEqual(url.params, 'a')
		self.assertEqual(url.fragment, 's')
		self.assertEqual(url.query.get('q'), ['a', 'b', 'c']) # sorted
		self.assertEqual(url.query.getfirst('q'), 'a')
		self.assertEqual(url.query.get('d'), ['f'])
		self.assertEqual(url.query.getfirst('d'), 'f')
		self.assertEqual(url.query.getfirst('b'), u'äåéëþüúíóöáßðfghïœøæœ©®bñ')
	
	def test_parse_hostname_unicode(self):
		'''It should not change unencoded internationalized domains'''
		
		url = URL(u'//www.ff¤ë.com')
		self.assertEqual(url.hostname, u'www.ff¤ë.com')
	
	def test_parse_hostname_punycode(self):
		'''It should decode internationalized domains'''
		
		url = URL(u'//www.x--ff-fda8z.com')
		self.assertEqual(url.hostname, u'www.ff¤ë.com')
	
	def test_collapse_path(self):
		'''It should normalize paths
		
		1. Leading slashes are removed.
		2. Double slahes are collapsed into one.
		3. Relative paths are simplified into the absolute paths
		4. Trailing slashes are removed
		'''
		
		s = '/a/b/c/../'
		self.assertEqual(urln11n.collapse_path(s), 'a/b')
		
		s = 'a/b/./c'
		self.assertEqual(urln11n.collapse_path(s), 'a/b/c')
		
		s = '/a/b/c/..'
		self.assertEqual(urln11n.collapse_path(s), 'a/b')
		
		s = 'a/../b/c'
		self.assertEqual(urln11n.collapse_path(s), 'b/c')
		
		s = '/a//b/'
		self.assertEqual(urln11n.collapse_path(s), 'a/b')
	
	def test_default_port_removal(self):
		'''It should accept a URL with the default port for that protocol and
		return the URL without the default port'''
		
		s = 'http://example.com:80'
		url = URL(s)
		self.assertEqual(str(url), 'http://example.com')
	
	def test_to_punycode_hostname(self):
		'''It should correctly encode the international domain'''
		
		s = u'aa.bb.cc.ačbǔcŏdīe¤f¤.com'
		self.assertEqual(urln11n.to_punycode_hostname(s), 
			'aa.bb.cc.x--abcdef-mhab25gxirn86c.com')
		self.assertEqual(urln11n.to_punycode_hostname('example.com'), 
			'example.com')
	
	def test_from_punycode_hostname(self):
		'''It should correctly decode the punycode domain'''
		
		s = 'aa.bb.cc.x--abcdef-mhab25gxirn86c.com'
		self.assertEqual(urln11n.from_punycode_hostname(s), 
			u'aa.bb.cc.ačbǔcŏdīe¤f¤.com')
		self.assertEqual(urln11n.from_punycode_hostname('example.com'), 
			'example.com')
	
	def test_is_allowable_hostname(self):
		'''It should return `True` if the domain has acceptable characters'''
		
		self.assertTrue(urln11n.is_allowable_hostname('www.example.com'))
		self.assertFalse(urln11n.is_allowable_hostname(u'www.bbéë.com'))
	
	def test_norm_unicode_http(self):
		'''It should normalize the URL with a internation domain'''
		
		s = u'http://sss.crrffœ³³³éåð.com/ßß³ /dd?df=4ëfð'
		url = URL(s)
		self.assertEqual(str(url), 'http://sss.x--crrff-5iaaa46bib4e48d.com' \
			'/%C3%9F%C3%9F%C2%B3%20/dd?df=4%C3%ABf%C3%B0')
	
	def test_norm_http_query_order(self):
		'''It should sort querys by keys and then values'''
		
		s = u'http://a.c/p?q=b&q=c&q=a'
		url = URL(s)
		self.assertEqual(str(url), 'http://a.c/p?q=a&q=b&q=c')
	
	def test_norm_http_ending_slash_and_empty_query(self):
		'''It should remove trailing slash and empty queries'''
		
		self.assertEqual(str(URL('http://ex.com/')), 'http://ex.com')
		self.assertEqual(str(URL('http://ex.com/?d')), 'http://ex.com?d')
		self.assertEqual(str(URL('http://ex.com/a/')), 'http://ex.com/a')
		self.assertEqual(str(URL('http://ex.com/a/a/?d')), 
			'http://ex.com/a/a?d')


