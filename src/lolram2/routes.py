# encoding=utf8

'''URL path routing'''

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

from lolram2 import urln11n

class Router(object):
	def __init__(self):
		self.data = {}
		self.default = None
	
	def get(self, route, default=None):
		if isinstance(route, str) or isinstance(route, unicode):
			route = urln11n.URL(route).path.strip('/')
		
		if default is None:
			default = self.default
			
		if isinstance(route, str) or isinstance(route, unicode):
			parts = route.split('/')
			for i in reversed(range(1, len(parts) + 1)):
				result = self.data.get('/'.join(parts[:i]))
				
				if result is not None:
					return result
			return default
		else:
			return self.data.get(route, default)
	
	def set(self, route, data, default=False):
		if isinstance(route, str) or isinstance(route, unicode):
			route = urln11n.URL(route).path.strip('/')
		self.data[route] = data
		
		if default:
			self.default = data
	
	def set_default(self, data):
		self.default = data
