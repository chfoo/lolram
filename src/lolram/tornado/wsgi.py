# encoding=utf8

'''WSGI Tornado adaptor to call WSGI applications'''

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

import wsgiref.util
import tornado.wsgi

def request_to_wsgi_call(handler, request, app, script_name=None):
	environ = tornado.wsgi.WSGIContainer.environ(request)
#	environ['REQUEST_URI'] = request.full_url()

	script_name = script_name.strip('/')
	
	for i in xrange(len(script_name.split('/'))):
		wsgiref.util.shift_path_info(environ)
	
	def start_response(status, headers):
		handler.set_status(int(status[:3]))
		
		for name, value in headers:
			handler.set_header(name, value)
		
		return handler.write
	
	response = app(environ, start_response)
	
	for i in response:
		handler.write(i)
	