'''Base classes for testing server'''
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
from wsgiref.simple_server import make_server
import http.client
import lolram.utils.url
import random
import threading
import time
import warnings
__docformat__ = 'restructuredtext en'

#import urllib3


class AppServerThread(threading.Thread):
	def __init__(self, app, port):
		threading.Thread.__init__(self)
		self.daemon = True
		self.app = app
		self.port = port
	
	def run(self):
		# XXX The wsgi validator cannot be used due to cgi.FieldStorage relying on
		# wsgi.input.readline() to take size as an argument
		app = self.app
		self.httpd = make_server('127.0.0.1', self.port, app)
		self.httpd.serve_forever()


class ServerBaseMixIn(object):
	def start_server(self):
		'''Start the server and application'''
		
		self.running = True
		self.thread = AppServerThread(self.app, random.randint(49152, 65535))
		self.thread.start()
		time.sleep(.5)
	
	def request(self, path, method='GET', headers={}, query_map={}, data={}, host=None, port=None):
		'''Make a HTTP request to the server
		
		:parameters:
			path : `str`
				The URL path
			method : `str`
				The HTTP request method. It is usually ``GET`` or ``POST``.
			headers : `dict`
				HTTP headers to send
			query_map : `dict`
				HTTP GET query
			data : `dict`
				Multi-part form data. 
				:see: `urllib3.encode_multipart_formdata`
		'''
		
		hc = http.client.HTTPConnection(host or '127.0.0.1', port or self.thread.port)
		
		path = str(lolram.utils.url.URL(path=path, query_map=query_map))
		
		if data:
			if method != 'POST':
				warnings.warn('Setting method to POST')
				method = 'POST'
			
			# FIXME: needs working urlib3 or reuse the function from it
			
			raise Exception('FIXME')
#			post_body, post_content_type = urllib3.encode_multipart_formdata(data)
#			headers['Content-Type'] = post_content_type
#			headers['Content-Length'] = len(post_body)
			
#			hc.request(method, path, post_body, headers)
		else:
			hc.request(method, path, None, headers)
		
		return hc.getresponse()
	
