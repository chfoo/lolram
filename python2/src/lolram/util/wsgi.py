# encoding=utf8

'''WSGI execution helpers'''

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

import optparse
import wsgiref.simple_server
import cStringIO
import gzip
import tempfile

import flup.server.fcgi

from lolram.util.routes import Router
from lolram.util.httpheaders import HTTPHeaders
from lolram.util import iterutils
import lolram.util.pathutil

class WSGIAppManager(object):
	'''Manages WSGI applications and requests'''
	
	def __init__(self, compress=True):
		self._router = Router()
		self._compress = compress
	
	@property
	def router(self):
		return self._router
	
	def run(self):
		option_parser = optparse.OptionParser()
		option_parser.add_option('-s', '--socket', dest='socket', 
			help='The Unix socket address in which to bind with',
			default='/tmp/lolram.socket')
		option_parser.add_option('-l', '--logfile', dest='logfile',
			help='The PATH of log file')
		option_parser.add_option('-p', '--port', dest='port',
			help='The TCP port used to bind the server')
		
		options, args = option_parser.parse_args()
		
		if options.port:
#			from rocket import Rocket
		
#			server = Rocket(('127.0.0.1', int(options.port)), 'wsgi', {"wsgi_app":self})
#			server.start()
			
			httpd = wsgiref.simple_server.make_server('', int(options.port), 
				self)
			httpd.serve_forever()

#			paste.httpserver.serve(self, port=int(options.port))
		else:
			socket_name = options.socket
			flup.server.fcgi.WSGIServer(self,
				bindAddress=socket_name).run()
		
	def __call__(self, environ, start_response):
		app = self.router.get(lolram.util.pathutil.request_uri(environ))
		
#		if self._compress:
#			return compress_app(app, environ, start_response)
		
		return app(environ, start_response)


	
def compress_app(app, environ, start_response):
	'''Compresses output from other apps'''
	nonlocals = dict(
		compress_ok = False,
		prespool = False,
		http_headers = None,
		orig_headers = None,
		orig_status = None,
	)
	
	def new_start_response(status, headers, nonlocals=nonlocals):
		nonlocals['orig_status'] = status
		nonlocals['orig_headers'] = headers
		http_headers = HTTPHeaders(items=headers)
		nonlocals['http_headers'] = http_headers
		
		if 'Content-Type' in http_headers \
		and http_headers['Content-Type'].startswith('text/') \
		and 'HTTP_ACCEPT_ENCODING' in environ \
		and environ['HTTP_ACCEPT_ENCODING'].find('gzip') != -1 \
		and 'Content-Encoding' not in http_headers:
			nonlocals['compress_ok'] = True
		
		if 'Content-Length' in http_headers and nonlocals['compress_ok']:
			nonlocals['prespool'] = True
			
		# FIXME: must return write callable
	
	r = iterutils.trigger(app(environ, new_start_response))
	
	compress_ok = nonlocals['compress_ok']
	prespool = nonlocals['prespool']
	http_headers = nonlocals['http_headers']
	orig_status = nonlocals['orig_status']
	orig_headers = nonlocals['orig_headers']
	
	if compress_ok:
		if prespool:
			file_obj = tempfile.SpooledTemporaryFile(max_size=1048576)
			compress_obj = gzip.GzipFile(mode='wb', fileobj=file_obj)
			
			for v in r:
				compress_obj.write(v)
			
			compress_obj.close()
			
			http_headers['Content-Length'] = str(file_obj.tell())
		
		http_headers['Content-Encoding'] = 'gzip'
		start_response(orig_status, http_headers.items())
	
		if prespool:
			file_obj.seek(0)
			while True:
				v = file_obj.read(4096)
				
				if v == '':
					break
				
				yield v
		else:
			file_obj = cStringIO.StringIO()
			compress_obj = gzip.GzipFile(mode='wb', fileobj=file_obj)
			
			for v in r:
				compress_obj.write(v)
				file_obj.seek(0)
				yield file_obj.read()
				file_obj.truncate(0)
			
			compress_obj.close()
			file_obj.seek(0)
			yield file_obj.read()
		
	else:
		start_response(orig_status, orig_headers)
		for v in r:
			yield v
