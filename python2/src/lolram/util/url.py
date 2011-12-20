# encoding=utf8

'''URL and URI utilities for normalization and canonicalization'''

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

import urlparse
import urllib
import copy
import cStringIO
import cgi

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
				vl = decode(value)
				vl.sort()
				self[key] = vl
		
		if query:
			for key, value in query.iteritems():
				if isinstance(value, list) or isinstance(value, tuple):
					vl = map(decode, value)
				else:
					vl = [decode(value)]
				
				self[key] = vl
	
	def getfirst(self, key, default=None):
		return self.get(key, (default,))[0]
	
	def __str__(self):
		q = []
		for key, value in sorted(self.iteritems(), key=lambda x:x[0]):
			if isinstance(value, list):
				for v in sorted(value):
					if not isinstance(v, str) and not isinstance(v, unicode):
						v = unicode(v)
					
					if v:
						q.append('%s=%s' % (urllib.quote(key.encode('utf8')),
							urllib.quote(unicode(v).encode('utf8'))))
					else:
						q.append(urllib.quote(key.encode('utf8')))
			else:
				if not isinstance(value, str) and not isinstance(value, unicode):
					value = unicode(value)
				
				q.append('%s=%s' % (urllib.quote(key.encode('utf8')),
					urllib.quote(value.encode('utf8'))))
		
		return '&'.join(q)
	
	
class URL(object):
	def __init__(self, string=None, scheme=None, username=None, 
	password=None, hostname=None, port=None, path=None, params=None,
	query=None, fragment=None, keep_trailing_slash=True):
		self._scheme = scheme
		self._username = username
		self._password = password
		self._hostname = hostname
		self._port = port
		self._path = path
		self._params = params
		self._query = URLQuery(query=query)
		self._fragment = fragment
		self._keep_trailing_slash = keep_trailing_slash
		self._has_trailing_slash = False
#		self.ajax_url = None
#		self.query_first = None
		
		self._string = string
		
		if self._string is not None:
			self.parse(self._string)
	
	@property
	def scheme(self):
		return self._scheme
	
	@scheme.setter
	def scheme(self, s):
		self._scheme = s
	
	@property
	def username(self):
		return self._username
	
	@username.setter
	def username(self, s):
		self._username = s
	
	@property
	def password(self):
		return self._password
	
	@password.setter
	def password(self, s):
		self._password = s
	
	@property
	def hostname(self):
		return self._hostname
	
	@hostname.setter
	def hostname(self, s):
		self._hostname = s
	
	@property
	def port(self):
		if self._port:
			return self._port
		else:
			return DEFAULT_PORTS.get(self.scheme)
	
	@port.setter
	def port(self, n):
		self._port = int(n)
	
	@property
	def path(self):
		slash = self._keep_trailing_slash or self.params and self._has_trailing_slash
		return collapse_path(self._path, slash)
	
	@path.setter
	def path(self, s):
		if not s.startswith('/'):
			s = u'/%s' % s
			
		self._has_trailing_slash = s.endswith(u'/')
		self._path = collapse_path(s, True)
	
	@property
	def params(self):
		return self._params
	
	@params.setter
	def params(self, s):
		self._params = unquote(s)
	
	@property
	def query(self):
		return self._query
	
	@query.setter
	def query(self, o):
		if isinstance(o, str) or isinstance(o, unicode):
			self._query = URLQuery(string=o)
		else:
			self._query = URLQuery(query=o)
	
	@property
	def fragment(self):
		return self._fragment
	
	@fragment.setter
	def fragment(self, s):
		self._fragment = s
	
	def __str__(self):
		s = cStringIO.StringIO()
		
		if self._scheme:
			s.write(self.scheme)
			s.write(':')
		
		if self._hostname:
			s.write('//')
		
		if self._username:
			s.write(urllib.quote_plus(self._username.encode('utf8')))
			
		if self._password:
			s.write(':')
			s.write(urllib.quote_plus(self._password.encode('utf8')))
		
		if self._username:
			s.write('@')
		
		if self._hostname:
			s.write(to_punycode_hostname(self._hostname))
		
		if self._port and DEFAULT_PORTS.get(self._scheme) != self._port:
			s.write(':')
			s.write(str(self._port))
		
		if self.path:
			s.write(urllib.quote(self.path.encode('utf8')))
		
		if self._params:
			s.write(';')
			s.write(self._params)
		
		if self._query:
			s.write('?')
			s.write(str(self._query))
		
		if self._fragment:
			s.write('#')
			s.write(urllib.quote(self._fragment.encode('utf8')))
		
		s.seek(0)
		return s.read()
		
	def __repr__(self):
		return '<URL (%s) at 0x%x>' % (self.__str__(), id(self))
	
	def to_string(self):
		return self.__str__()
	
	def parse(self, string):
		p = urlparse.urlparse(string)
		
		if p.path.endswith('/') and p.params:
			self._has_trailing_slash = True
		
		self.scheme = p.scheme
		self.path = p.path
		self.params = p.params
		self.query = URLQuery(string=p.query)
		
#		self.query_first = {}
#		
#		for key, values in q.iteritems():
#			self.query_first[key] = values[0]
			
		self.fragment = unquote(p.fragment)
		self.username = unquote(p.username)
		self.password = unquote(p.password)
		
		if p.hostname:
			self.hostname = from_punycode_hostname(p.hostname)
			
		self._port = p.port
		if self._port:
			self._port = int(self.port)
	
	def get_query_first(self):
		d = {}
		
		for k in self.query:
			d[k] = self.query.getfirst(k)
		
		return d
	
	def copy(self):
		return copy.copy(self)

class FieldStorage(cgi.FieldStorage):
	def getfirst(self, *args, **kargs):
		v = cgi.FieldStorage.getfirst(self, *args, **kargs)
		
		if isinstance(v, str):
			return v.decode('utf8')
		else:
			return v
	
	def getlist(self, *args, **kargs):
		l = cgi.FieldStorage.getlist(self, *args, **kargs)
		
		new_list = l
		
		for i in xrange(len(l)):
			v = l[i]
			
			if isinstance(v, str):
				new_list[i] = v.decode('utf8')
		
		return new_list

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

def decode(s):
	if isinstance(s, str):
		return s.decode('utf8')
	else:
		return s

def quote(s):
	return urllib.quote(s.encode('utf8'))

def collapse_path(s, keep_trailing_slash=True):
	l = []
	
	for part in s.replace('//', '/').split('/'):
		part = unquote(part)
		if part == u'..':
			if len(l):
				del l[-1]
				
				if s.endswith('..'):
					l.append('')
				
		elif (part or keep_trailing_slash) and part != u'.':
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

