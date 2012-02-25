'''URL and URI utilities for normalization and canonicalization'''
#
#	Copyright © 2011-2012 Christopher Foo <chris.foo@gmail.com>
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
__docformat__ = 'restructuredtext en'

import urllib.parse
import copy
import io
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

def bytes_to_str(bytes_or_str):
	'''Converts utf8 `bytes` to `str`
	
	If the argument is already `str`, it is left unchanged
	'''
	
	if isinstance(bytes_or_str, bytes):
		return bytes_or_str.decode()
	else:
		return bytes_or_str


class URLQuery(dict):
	'''A url query key and value list map
	
	The keys are `str`. The values are a `list` of `str`
	'''
	
	def __init__(self, encoded_string=None, query_map=None):
		'''Initialize a map
		
		:parameters:
			encoded_str : `str`, `byte`
				A percent-encoded URL query.
			query_map : `dict`
				A mapping of query values.
		'''
		
		if encoded_string:
			query_map = urllib.parse.parse_qs(encoded_string, True)
		
		if query_map:
			for key, value_list in query_map.items():
				key = bytes_to_str(key)
				
				try:
					iter(value_list)
				except TypeError:
					value_list = [value_list]
				
				value_list = list(map(bytes_to_str, value_list))
				value_list.sort()
				self[key] = value_list
	
	def getfirst(self, key, default=None):
		'''Get the first value for a key
		
		:rtype: `str`
		'''
		
		return self.get(key, (default,))[0]
	
	def __str__(self):
		'''Return the percent-encoded url query form
		
		:rtype: `str`
		'''
		
		# Make sure everything is consistently `str` :)
		query_obj = URLQuery(query_map=self)
		
		q = []
		for key, value_list in sorted(iter(query_obj.items()), key=lambda x:x[0]):
			if value_list:
				for value in value_list:
					if value:
						q.append('%s=%s' % (urllib.parse.quote(key.encode()),
							urllib.parse.quote(value.encode())))
					else:
						q.append(urllib.parse.quote(key.encode()))
			else:
				q.append(urllib.parse.quote(key.encode()))
		
		return '&'.join(q)
	
	def to_key_value_map(self):
		'''Return a plain `dict` with key and first value'''
		
		new_dict = {}
		for key, value_list in self.items():
			new_dict[key] = value_list[0]
		
		return new_dict
	
class URL(object):
	'''A fancy URL parser and builder
	
	It helps with normalization and canonicalization of URLs.
	'''
	
	def __init__(self, encoded_string=None, scheme=None, username=None, 
	password=None, hostname=None, port=None, path=None, params=None,
	query_map=None, fragment=None, keep_trailing_slash=True):
		'''Initialze the URL object
		
		:parameters:
			encoded_str : `str`
				A percent-encoded, punycode-encoded URL string
			scheme: `str`
				The scheme portion. For example, http and ftp.
			username: `str`
				The username portion.
			password: `str`
				The password portion.
			hostname: `str`
				The hostname portion.
			port: `int`
				The port number.
			path: `str`
				The path portion without the parameter portion.
			params: `str`
				The parameters portion.
			query_map: `dict`
				A key and value list map of query values.
			fragment: `str`
				The fragment portion
			keep_trailing_slash: `bool`
				If `True`, the trailing slash of the path is not stripped.
				Technically, a trailing slash indicates a directory and a 
				non-trailing slash indicate a file. However, this semantic
				is not intuitive to regular web users. On a search engine
				optimization perspective, the trailing slash usually matters.
		'''
	
		self._scheme = scheme
		self._username = username
		self._password = password
		self._hostname = hostname
		self._port = port
		self._path = path
		self._params = params
		self._query = URLQuery(query_map=query_map)
		self._fragment = fragment
		self._keep_trailing_slash = keep_trailing_slash
		self._has_trailing_slash = False
		# TODO: maybe some ajax url parsing as well?
#		self.ajax_url = None
		
		if encoded_string is not None:
			self.parse(encoded_string)
	
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
			s = '/%s' % s
			
		self._has_trailing_slash = s.endswith('/')
		self._path = collapse_path(s, True)
	
	@property
	def params(self):
		return self._params
	
	@params.setter
	def params(self, s):
		self._params = urllib.parse.unquote(s)
	
	@property
	def query(self):
		return self._query
	
	@query.setter
	def query(self, o):
		if isinstance(o, str) or isinstance(o, bytes):
			self._query = URLQuery(encoded_string=o)
		else:
			self._query = URLQuery(query_map=o)
	
	@property
	def fragment(self):
		return self._fragment
	
	@fragment.setter
	def fragment(self, s):
		self._fragment = s
	
	def __str__(self):
		s = io.StringIO()
		
		if self._scheme:
			s.write(self.scheme)
			s.write(':')
		
		if self._hostname:
			s.write('//')
		
		if self._username:
			s.write(urllib.parse.quote_plus(self._username.encode()))
			
		if self._password:
			s.write(':')
			s.write(urllib.parse.quote_plus(self._password.encode()))
		
		if self._username:
			s.write('@')
		
		if self._hostname:
			s.write(to_punycode_hostname(self._hostname))
		
		if self._port and DEFAULT_PORTS.get(self._scheme) != self._port:
			s.write(':')
			s.write(str(self._port))
		
		if self.path:
			s.write(urllib.parse.quote(self.path.encode()))
		
		if self._params:
			s.write(';')
			s.write(self._params)
		
		if self._query:
			s.write('?')
			s.write(str(self._query))
		
		if self._fragment:
			s.write('#')
			s.write(urllib.parse.quote(self._fragment.encode()))
		
		s.seek(0)
		return s.read()
		
	def __repr__(self):
		return '<URL (%s) at 0x%x>' % (self.__str__(), id(self))
	
	def to_string(self):
		return self.__str__()
	
	def parse(self, string):
		
		p = urllib.parse.urlparse(bytes_to_str(string))
		
		if p.path.endswith('/') and p.params:
			self._has_trailing_slash = True
		
		self.scheme = p.scheme
		self.path = p.path
		self.params = p.params
		self.query = URLQuery(encoded_string=p.query)
		
		if p.fragment:
			self.fragment = urllib.parse.unquote(p.fragment)
		
		if p.username:
			self.username = urllib.parse.unquote(p.username)
		
		if p.username:
			self.password = urllib.parse.unquote(p.password)
		
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
		
		for i in range(len(l)):
			v = l[i]
			
			if isinstance(v, str):
				new_list[i] = v.decode('utf8')
		
		return new_list

def is_allowable_hostname(s):
	# 
	return all([c in ('-', '.') or 48 <= ord(c) <= 57 or 97 <= ord(c) <= 127 for c in s])

def normalize(s):
	return str(URL(s))

#def unquote(s):
#	if s is None:
#		return None
#	
#	try:
#		return urllib.parse.unquote(s).decode('utf8')
#	except UnicodeEncodeError:
#		try:
#			return urllib.parse.unquote(str(s)).decode('utf8')
#		except UnicodeEncodeError:
#			return s
#
#def decode(s):
#	if isinstance(s, str):
#		return s.decode('utf8')
#	else:
#		return s
#
#def quote(s):
#	return urllib.parse.quote(s.encode('utf8'))


def collapse_path(s, keep_trailing_slash=True):
	l = []
	
	for part in s.replace('//', '/').split('/'):
		part = urllib.parse.unquote(part)
		if part == '..':
			if len(l):
				del l[-1]
				
				if s.endswith('..'):
					l.append('')
				
		elif (part or keep_trailing_slash) and part != '.':
			l.append(part)
	
	return '/'.join(l)

def from_punycode_hostname(s):
	if not is_allowable_hostname(s):
		return s
	else:
		s = str(s)
	
	h = s.split('.')
	if len(h) > 1 and h[-2].startswith('x--'):
		h[-2] = bytes(h[-2].replace('x--', '', 1), 'utf8').decode('punycode')
	return '.'.join(h)

def to_punycode_hostname(s):
	if is_allowable_hostname(s):
		return s
	else:
		h = s.split('.')
		h[-2] = 'x--' + str(h[-2].encode('punycode'), 'utf8')
		return '.'.join(h)

