# encoding=utf8

'''Enhanced HTTP header management'''

#	Copyright © 2010–2011 Christopher Foo <chris.foo@gmail.com>

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

import UserDict
import cStringIO
import string

from lolram2 import urln11n

class HTTPHeaders(UserDict.DictMixin):
	'''A dictionary-like mapping of HTTP Headers
	
	Dictionary-like operations will behave in the manner of `get_first`. 
	That is, dictionary-like operations will assume that only unique header 
	names exists.
	'''
	
	def __init__(self, environ=None, read_only=False, items=None):
		self.data = {}
		self.read_only = False
	
		if environ is not None:
			for key, value in environ.iteritems():
				if key.startswith('HTTP_'):
					name = key.replace('HTTP_', '', 1)
					header = self.parse_header(name, value)
					self.add(header)
		
		self.read_only = read_only
		
		if items:
			for item in items:
				header = HTTPHeader(item[0], item[1])
				self.add(header)
	
	def _check_read_only(self):
		if self.read_only:
			raise AttributeError('Read-only')
					
	def __getitem__(self, name):
		return str(self.data[normalize_header_name(name)][0])
	
	def __setitem__(self, name, value):
		self._check_read_only()
		self.data[normalize_header_name(name)] = [self.parse_header(name, value)]
	
	def __delitem__(self, name):
		self._check_read_only()		
		del self.data[normalize_header_name(name)]
	
	def __contains__(self, name):
		return normalize_header_name(name) in self.data
	
	def __iter__(self):
		return iter(self.data)
	
	def get_list(self, name, default=None):
		'''Return a list of `HTTPHeader`
		
		:rtype: `list`
		'''
		
		return self.data.get(normalize_header_name(name), default)
	
	def get_first(self, name, default=None):
		'''Return the first value for the header name
		
		:rtype: `HTTPHeader`
		'''
		
		v = self.data.get(normalize_header_name(name), default)
		if isinstance(v, list):
			return v[0]
		else:
			return v
	
	def add_header(self, name, value, **params):
		'''Add a header value'''
		
		self.add(HTTPHeader(name, value, **params))
	
	def add(self, header):
		'''Add a `HTTPHeader` instance'''
		
		self._check_read_only()
		if header.name not in self.data:
			self.data[header.name] = []
		
		self.data[header.name].append(header)
	
	def parse_header(self, name, value):
		header = HTTPHeader(name)
		
		if value.find(';') != -1:
			header.value, sep, vl = value.partition(',')
			del sep
		
			for i in vl.split(';'):
				k, sep, v = i.partition('=')
				k = k.strip()
				v = v.strip()
				del sep
			
				if k:
					header.params[k] = v
		
		else:
			header.value = value
		
		return header
	
	def __str__(self):
		s = cStringIO.StringIO()
		for name in self:
			for header in self.get_list(name):
				s.write(normalize_header_name(name))
				s.write(': ')
				s.write(str(header))
				s.write('\n\r')
		
		s.seek(0)
		return s.read()
	
	def items(self):
		l = []
		for name in self:
			for header in self.get_list(name):
				l.append((normalize_header_name(name), str(header)))
		return l
	

class HTTPHeader(object):
	'''Represents a HTTP header value with optional parameters
	
	Example::
		Header-Name: header_value;param1=val1;param2=val2
	'''
	
	def __init__(self, name=None, value=None, **params):
		if name:
			self._name = normalize_header_name(name)
		else:
			self._name = None
		self._value = value
		self._params = params
	
	def __str__(self):
		s = cStringIO.StringIO()
		s.write(self.value)
		for k, v in sorted(self.params.iteritems()):
			s.write('; ')
			s.write(normalize_header_name(k, capwords=False))
			s.write('=')
			s.write(urln11n.quote(v))
		
		s.seek(0)
		return s.read()
	
	@property
	def value(self):
		return self._value
	
	@value.setter
	def value(self, v):
		self._value = v
	
	@property
	def params(self):
		return self._params
	
	@property
	def name(self):
		return self._name
	
	@name.setter
	def name(self, s):
		self._name = s

def normalize_header_name(name, capwords=True):
	if capwords:
		return string.capwords(name.replace('_', '-'), '-')
	else:
		return name.replace('_', '-')