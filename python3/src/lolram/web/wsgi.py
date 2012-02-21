'''WSGI middleware applications'''
#
#	Copyright © 2011 Christopher Foo <chris.foo@gmail.com>
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
import gzip
import io
import logging
import lolram.web.headers
import tempfile
import urllib.parse

__docformat__ = 'restructuredtext en'

_logger = logging.getLogger(__name__)

class PathRouter(object):
	'''Routes applications based on URL path'''
	
	def __init__(self, routes):
		self.routes = routes
	
	def __call__(self, environ, start_response):
		incoming_path = environ['PATH_INFO']
		result = self.routes.get(incoming_path)
		
		return result(environ, start_response)


class Compressor(object):
	'''Applies compression to responses'''
	
	SIZE_10KB = 10240
	SIZE_1MB = 1048576
	METHOD_SPOOLING = 'spool'
	METHOD_STREAMING = 'steam'
	CHUNK_SIZE = 8192 # 8 KB
	
	class SpooledFile(object):
		def __init__(self, memory_spool_size):
			self.temp_file = tempfile.SpooledTemporaryFile(
				max_size=memory_spool_size)
			self.gzip_file = gzip.GzipFile(mode='wb', fileobj=self.temp_file)
		
		def write(self, data):
			self.gzip_file.write(data)
		
		def switch(self, values):
			for v in values:
				self.gzip_file.write(v)
		
		def close(self):
			self.gzip_file.close()
	
	class StreamingFile(object):
		class WriteCallableWrapper(object):
			def __init__(self, file_obj):
				self.file_obj = file_obj
			
			def write(self, data):
				print('wrote', len(data), 'bytes',)
				self.file_obj.write(data)
			
			def flush(self):
				self.file_obj.flush()
		
		def __init__(self, write_callable):
			self.write_wrapper = Compressor.StreamingFile.WriteCallableWrapper(
				write_callable)
			self.gzip_file = gzip.GzipFile(mode='wb', 
				fileobj=self.write_wrapper)
		
		def write(self, data):
			self.gzip_file.write(data)
		
		def switch(self, values):
			self.gzip_file.flush()
			self.write_wrapper.file_obj = io.BytesIO()
			self.iterator = values
		
		def close(self):
			self.gzip_file.close()
		
		def __iter__(self):
			f = self.write_wrapper.file_obj
			
			for v in self.iterator:
				self.write(v)
				f.seek(0)
				yield f.read()
				f.truncate(0)
			
			f.seek(0)
			self.close()
			f.seek(0)
			yield f.read()

	def __init__(self, application, cache=None, 
	memory_spool_size=None,
	spooling_fail_limit=None):
		self.application = application
		self.cache = cache
		self.memory_spool_size = memory_spool_size or Compressor.SIZE_10KB
		self.spooling_fail_limit = spooling_fail_limit or Compressor.SIZE_1MB
	
	def is_compressable(self, environ, headers_dict):
		content_length = int(headers_dict.get('Content-Length', -1))
		
		return headers_dict.get('Content-Type', '').startswith('text/') \
			and environ.get('HTTP_ACCEPT_ENCODING', '').find('gzip') != -1 \
			and 'Content-Encoding' not in headers_dict \
			and content_length < self.spooling_fail_limit
	
	def __call__(self, environ, start_response):
		output_sink = None
		compression_method = None
		headers_dict = None
		response_status = None
		response_exc_info = None
		
		def new_start_response(status, response_headers, exc_info=None):
			nonlocal output_sink, compression_method, headers_dict, \
				response_status, response_exc_info
			
			response_status = status #@UnusedVariable
			response_exc_info = exc_info #@UnusedVariable
			headers_dict = lolram.web.headers.HeaderListMap(response_headers)
			
			if self.is_compressable(environ, headers_dict):
				content_length = int(headers_dict.get('Content-Length', -1))
				
				headers_dict['Content-Encoding'] = 'gzip'
				
				if content_length >= 0:
					compression_method = Compressor.METHOD_SPOOLING
					output_sink = Compressor.SpooledFile(self.memory_spool_size)
				else:
					compression_method = Compressor.METHOD_STREAMING
					write_callable = start_response(status, headers_dict.to_list(), exc_info)
					output_sink = Compressor.StreamingFile(write_callable)
				
				return output_sink
			else:
				return start_response(status, response_headers, exc_info)
		
		app_iterator = self.application(environ, new_start_response)
		
		if output_sink:
			if compression_method == Compressor.METHOD_SPOOLING:
				spooled_file = output_sink.temp_file
				
				output_sink.switch(app_iterator)
				output_sink.close()
				headers_dict['Content-Length'] = str(spooled_file.tell())
				
				spooled_file.seek(0)
				
				start_response(response_status, headers_dict.to_list(), 
					response_exc_info)
				
				with spooled_file:
					while True:
						data = spooled_file.read(Compressor.CHUNK_SIZE)
						
						if data == b'':
							break
						
						yield data
			else:
				output_sink.switch(app_iterator)
				
				for v in output_sink:
					yield v
		else:
			for v in app_iterator:
				yield v
		
class StripDummyAppPath(object):
	'''Strips the dummy app path provided in SCRIPT_NAME even though
	the user does not see the dummy app path
	'''
	
	def __init__(self, app, prefix='/dummy.fcgi'):
		self.app = app
		self.prefix = prefix
	
	def __call__(self, environ, start_response):
		new_script_name = environ['SCRIPT_NAME'].replace(
			self.prefix, '', 1)
		new_path_info = environ['PATH_INFO'].replace(
			self.prefix, '', 1)
		
		_logger.debug('SCRIPT_NAME %s to %s', environ['SCRIPT_NAME'], new_script_name)
		_logger.debug('PATH_INFO %s to %s', environ['PATH_INFO'], new_path_info)
#		_logger.debug('REQUEST_URI %s', environ.get('REQUEST_URI'))
		
		environ['SCRIPT_NAME'] = new_script_name
		environ['PATH_INFO'] = new_path_info
		return self.app(environ, start_response)


#class DecodeNonConformingPathInfo(object):
#	'''Attempts to decode PATH_INFO that is left as percent-encoded.
#	
#	It will try to decode as utf8, then latin1 as specified in wsgi specs
#	for python 3. It does not channel utf8 bytes as latin1!
#	
#	:note: Only use this app if definitely know that your server
#		does not conform
#	'''
#	
#	def __init__(self, app):
#		self.app = app
#	
#	def __call__(self, environ, start_response):
#		new_path_info = urllib.parse.unquote(environ['PATH_INFO'])
#		
#		_logger.debug('PATH_INFO %s to %s', environ['PATH_INFO'], new_path_info)
#		
#		environ['PATH_INFO'] = new_path_info
#		return self.app(environ, start_response)

class DecodeFromLatin1ToUnicode(object):
	'''Decodes utf8 bytes channelled into latin1 to unicode'''
	
	def __init__(self, app):
		self.app = app
	
	def __call__(self, environ, start_response):
		new_path_info = environ['PATH_INFO'].encode('latin1').decode('utf8')
#		new_request_uri = environ['REQUEST_URI'].encode('latin1').decode('utf8')
		
		_logger.debug('PATH_INFO %s to %s', environ['PATH_INFO'], new_path_info)
#		_logger.debug('REQUEST_URI %s to %s', environ['REQUEST_URI'], new_request_uri)
		
		environ['PATH_INFO'] = new_path_info
#		environ['REQUEST_URI'] = new_request_uri
		return self.app(environ, start_response)
	