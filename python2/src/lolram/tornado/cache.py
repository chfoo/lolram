# encoding=utf8

'''Support for Memcached'''

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

import memcache

class MemcacheWrapper(object):
	def __init__(self, hosts, prefix):
		self._client = memcache.Client(hosts)
		self._prefix = prefix
	
	def get(self, key):
		return self._client.get('%s%s' % (self._prefix, key))
	
	def set(self, key, value): #@ReservedAssignment
		self._client.set('%s%s' % (self._prefix, key), value)

class CacheMixIn(object):
	'''MongoDB database support mix-in class for Tornado RequestHandler'''
	
	def initialize(self, hosts=['localhost:11211'], prefix='lolram'):
		self._cache = MemcacheWrapper(hosts, prefix)
	
	@property
	def cache(self):
		return self._cache



