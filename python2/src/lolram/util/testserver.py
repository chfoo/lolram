# encoding=utf8

'''Base classes for testing server'''
from wsgiref.simple_server import make_server
import httplib
import lolram.util.url
import random
import threading
import time
import urllib3
import warnings

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


class AppServerThread(threading.Thread):
	'''Starts a server'''
	
	def __init__(self, app, port=181000):
		threading.Thread.__init__(self)
		self.app = app
		self.daemon = True
		self.port = port
	
	def run(self):
		# XXX The wsgiref.validate.validator cannot be used due to cgi.FieldStorage
		# relying on wsgi.input.readline() to take size as an argument
		app = self.app
		self.httpd = make_server('', self.port, app)
		self.httpd.serve_forever()

class Server(object):
	'''Server'''
	
	def __init__(self, app, port=None):
		self.app = app
		self.port = port if port else random.randint(49152, 65535)
	
	def start(self):
		'''Start the server and application'''
		
		self.thread = AppServerThread(self.app, self.port)
		self.thread.start()
		time.sleep(0.1)
	
	def stop(self):
		self.thread.httpd.shutdown()
	
	def request(self, path, method='GET', headers={}, query={}, data={}, host=None, port=None):
		'''Make a HTTP request to the server
		
		:parameters:
			path : `str`
				The URL path
			method : `str`
				The HTTP request method. It is usually ``GET`` or ``POST``.
			headers : `dict`
				HTTP headers to send
			query : `dict`
				HTTP GET query
			data : `dict`
				Multi-part form data. 
				:see: `urllib3.encode_multipart_formdata`
		
		:rtype: `httplib.HTTPResponse`
		'''
		
		hc = httplib.HTTPConnection(host or '127.0.0.1', port or self.thread.port)
		
		path = str(lolram.util.url.URL(path=path, query=query))
		
		if data:
			if method != 'POST':
				warnings.warn('Setting method to POST')
				method = 'POST'
			
			post_body, post_content_type = urllib3.encode_multipart_formdata(data)
			headers['Content-Type'] = post_content_type
			headers['Content-Length'] = len(post_body)
			
			hc.request(method, path, post_body, headers)
		else:
			hc.request(method, path, None, headers)
		
		return hc.getresponse()
	
