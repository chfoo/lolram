# encoding=utf8

'''URL normalization (URL canonicalization)'''

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

__doctype__ = 'restructuredtext en'

import urlparse
import urllib
import copy

DEFAULT_PORTS = {
	'ftp' : 21,
	'gopher' : 70,
	'hdl' : 2641,
	'http' : 80,
	'https' : 443,
	'imap' : 143,
	'nntp' : 119,
	'propsero' : 191,
	'rsync' : 873,
	'rtsp' : 554,
	'sftp' : 115,
	'sip' : 5060,
	'svn' : 3690,
	'telnet' : 23,
}

class URLQuery(dict):
	def __init__(self, string=None, query=None):
		if string:
			q = urlparse.parse_qs(string, True)
		
			for key, value in q.iteritems():
				vl = map(unquote, value)
				vl.sort()
				self[key] = vl
		
		if query:
			for key, value in query.iteritems():
				if isinstance(value, list) or isinstance(value, tuple):
					vl = value
				else:
					vl = [value]
				
				self[key] = vl
	
	def getfirst(self, key, default=None):
		return self.get(key, (default,))[0]
	
	def __str__(self):
		q = []
		for key, value in sorted(self.iteritems(), key=lambda x:x[0]):
			if isinstance(value, list):
				for v in sorted(value):
					if v:
						q.append('%s=%s' % (urllib.quote(key.encode('utf8')),
							urllib.quote(unicode(v).encode('utf8'))))
					else:
						q.append(urllib.quote(key.encode('utf8')))
			else:
				q.append('%s=%s' % (urllib.quote(key.encode('utf8')),
					urllib.quote(value.encode('utf8'))))
		
		return '&'.join(q)
	
	
class URL(object):
	def __init__(self, string=None, scheme=None, username=None, 
	password=None, hostname=None, port=None, path=None, params=None,
	query=None, fragment=None):
		self.scheme = scheme
		self.username = username
		self.password = password
		self.hostname = hostname
		self.port = port
		self.path = path
		self.params = params
		self.query = URLQuery(query=query)
		self.fragment = fragment
#		self.ajax_url = None
#		self.query_first = None
		
		self.string = string
		
		if self.string is not None:
			self.parse(self.string)
	
	def __str__(self):
		l = []
		if self.scheme:
			l.append(self.scheme)
			l.append(':')
		
		if self.hostname:
			l.append('//')
		
		if self.username:
			l.append(urllib.quote_plus(self.username.encode('utf8')))
			
		if self.password:
			l.append(':')
			l.append(urllib.quote_plus(self.password.encode('utf8')))
		
		if self.username:
			l.append('@')
		
		if self.hostname:
			l.append(to_punycode_hostname(self.hostname))
		
		if self.port and DEFAULT_PORTS.get(self.scheme) != self.port:
			l.append(':')
			l.append(str(self.port))
		
		if self.path and not self.path.startswith('/') and self.path != '/':
			l.append('/')
		if self.path and self.path != '/':
			l.append(urllib.quote(self.path.encode('utf8')))
		
		if self.params:
			l.append(';')
			l.append(self.params)
		
		if self.query:
			l.append('?')
			l.append(str(self.query))
		
		if self.fragment:
			l.append('#')
			l.append(urllib.quote(self.fragment.encode('utf8')))
		
		return ''.join(l)
		
	def __repr__(self):
		return '<URL (%s) at 0x%x>' % (self.__str__(), id(self))
	
	def to_string(self):
		return self.__str__()
	
	def parse(self, string):
		p = urlparse.urlparse(string)
		
		self.scheme = p.scheme
		self.path = collapse_path(p.path)
		self.params = unquote(p.params)
		self.query = URLQuery(p.query)
		
#		self.query_first = {}
#		
#		for key, values in q.iteritems():
#			self.query_first[key] = values[0]
			
		self.fragment = unquote(p.fragment)
		self.username = unquote(p.username)
		self.password = unquote(p.password)
		
		if p.hostname:
			self.hostname = from_punycode_hostname(p.hostname)
			
		self.port = p.port
		if self.port:
			self.port = int(self.port)
	
	def copy(self):
		return copy.copy(self)

def is_allowable_hostname(s):
	# 
	return all([c in ('-', '.') or 48 <= ord(c) <= 57 or 97 <= ord(c) <= 127 for c in s])

def normalize(s):
	return str(URL(s))

def unquote(s):
	if s is None:
		return None
	
	try:
		return urllib.unquote(s).decode('utf8')
	except UnicodeEncodeError:
		try:
			return urllib.unquote(str(s)).decode('utf8')
		except UnicodeEncodeError:
			return s

def quote(s):
	return urllib.quote(s.encode('utf8'))

def collapse_path(s):
	l = []
	
	for part in s.replace('//', '/').split('/'):
		part = unquote(part)
		if part == u'..':
			if len(l):
				del l[-1]
		elif part and part != u'.':
			l.append(part)
	
	return u'/'.join(l)

def from_punycode_hostname(s):
	if not is_allowable_hostname(s):
		return s
	else:
		s = str(s)
	
	h = s.split('.')
	if len(h) > 1 and h[-2].startswith('x--'):
		h[-2] = h[-2].replace('x--', '', 1).decode('punycode')
	return '.'.join(h)

def to_punycode_hostname(s):
	if is_allowable_hostname(s):
		return s
	else:
		h = s.split('.')
		h[-2] = 'x--' + h[-2].encode('punycode')
		return '.'.join(h)

