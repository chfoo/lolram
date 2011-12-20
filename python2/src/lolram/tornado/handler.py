#encoding=utf8

'''Pre-built rich featured handlers'''

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

import tornado.web

import lolram.tornado.mongodb
import lolram.tornado.session
import lolram.tornado.message
import lolram.tornado.navigation
import lolram.tornado.form
import lolram.tornado.static
import lolram.tornado.cache 
import lolram.tornado.wsgi

class RichBaseHandler(lolram.tornado.wsgi.RequestHandlerGenerator,
lolram.tornado.mongodb.DatabaseMixIn,
lolram.tornado.session.SessionMongoDBMixIn,
lolram.tornado.message.MessageMixIn,
lolram.tornado.navigation.NavigationMixIn,
lolram.tornado.form.FormHandlerMixIn,
lolram.tornado.static.StaticFileHandlerMixIn,
lolram.tornado.cache.CacheMixIn,
):
	'''A rich featured base RequestHandler'''
	
	def initialize(self, mongodb, cache_hosts, cache_prefix, **kargs):
		lolram.tornado.mongodb.DatabaseMixIn.initialize(self, mongodb)
		lolram.tornado.cache.CacheMixIn.initialize(self, cache_hosts, cache_prefix)
	
	def prepare(self):
		lolram.tornado.message.MessageMixIn.prepare(self)
		lolram.tornado.navigation.NavigationMixIn.prepare(self)
		self.setup_session()
		tornado.web.RequestHandler.prepare(self)
	
	
	def finish(self, *args, **kargs):
		self.save_session()
		return lolram.tornado.wsgi.RequestHandlerGenerator.finish(self, 
			*args, **kargs)
	
	def is_local(self):
		return self.request.host.split(':')[0] in ('127.0.0.1', 'localhost')
	
	def clear(self):
		headers_to_restore = {}
		
		if hasattr(self, '_status_code'):
			if 'WWW-Authenticate' in self._headers:
				headers_to_restore['WWW-Authenticate'] = self._headers['WWW-Authenticate']
		
		tornado.web.RequestHandler.clear(self)
		
		for key, value in headers_to_restore.iteritems():
			self.set_header(key, value)
	