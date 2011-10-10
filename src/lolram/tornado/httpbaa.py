# encoding=utf8

'''HTTP Basic Authentication Access'''

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

class HTTPBAAHanderMixIn(object):
	def require_baa(self, callback, realm=None):
		if not realm:
			realm = self.request.host
		
		auth_header = self.request.headers.get('authorization')
		
		username = None
		password = None
		
		if auth_header \
		and auth_header.startswith('Basic '):
			plain = auth_header[6:].decode('base64')
			username, password = plain.split(':', 1)
			
		if username and callback(username, password):
			self.request.httpbaa_username = username
			self.request.httpbaa_password = password
		else:
			self.set_header('WWW-Authenticate', 'Basic Realm="%s"' % realm)
			raise tornado.web.HTTPError(401)
		
		