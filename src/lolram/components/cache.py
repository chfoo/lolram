# encoding=utf8

'''Cache'''

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

import base
from .. import configloader

class Cache(base.BaseComponent):
	default_config = configloader.DefaultSectionConfig('cache',
		servers='localhost:11211'
	)
	
	def init(self):
		self._client = memcache.Client(self.context.config.cache.servers.split())
	
	def set(self, key, value):
		if not self.context.is_testing:
			key = hash_key(self.context, key)
			self.context.logger.debug(u'Cache set %s %s', key, value)
			self.singleton._client.set(key, value)
	
	def get(self, key):
		if not self.context.is_testing:
			key = hash_key(self.context, key)
			value = self.singleton._client.get(key)
			self.context.logger.debug(u'Cache get %s %s', key, value)
			return value
	
	def cleanup(self):
		self.context.logger.debug(unicode(self.singleton._client.get_stats()))
	
def hash_key(context, key):
	return '%s%s' % (context.dirinfo.app, key)