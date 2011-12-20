# encoding=utf8

'''WSGI Tornado adaptor to call WSGI applications'''

# BEGIN GPL code

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

import httplib
import urllib
import cgi
import time
import logging
import wsgiref.util
import tornado.wsgi
import tornado.web
import tornado.escape

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

# END GPL code

# BEGIN Apache License code

# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#	 http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

class WSGIApplicationGenerator(tornado.wsgi.WSGIApplication):
	def __init__(self, handlers=None, default_host="", **settings):
		transforms = []
		
		if settings.get('gzip'):
			transforms.append(tornado.web.GZipContentEncoding)
		
		tornado.web.Application.__init__(self, handlers, default_host, 
			transforms=transforms,
			wsgi=True, **settings)	
	
	def __call__(self, environ, start_response):
		request = HTTPRequestGenerator(environ)
#		try:
		handler, transforms, args, kwargs = self.call2(request)
#		except Exception, e:
#			sys.stderr.write(str(e))
#			sys.stderr.write('\n')
#			raise e
		
		if hasattr(handler.request, 'parse_request_body'):
			handler.request.parse_request_body(environ, 
				getattr(handler, 'USE_FIELDSTORAGE', False))
		
		if hasattr(handler, 'USE_COROUTINE'):
			def coroutine():
				status = str(handler._status_code) + " " + \
				httplib.responses[handler._status_code]
				headers = handler._headers.items()
				
				for cookie_dict in getattr(handler, "_new_cookies", []):
					for cookie in cookie_dict.values():
						headers.append(("Set-Cookie", cookie.OutputString(None)))
				
				write_hax_fn = start_response(status,
					[(tornado.escape.native_str(k), tornado.escape.native_str(v)) for (k,v) in headers])
				
				assert write_hax_fn
				
				while True:
					v = (yield)
					write_hax_fn(v)
			
			handler._write_coroutine = coroutine()
			handler._execute(transforms, *args, **kwargs)
			
			yield ''
			
			for v in handler._write_buffer:
				yield v
			
		else:
			handler._execute(transforms, *args, **kwargs)
			assert handler._finished
			status = str(handler._status_code) + " " + \
				httplib.responses[handler._status_code]
			headers = handler._headers.items()
			
			for cookie_dict in getattr(handler, "_new_cookies", []):
				for cookie in cookie_dict.values():
					headers.append(("Set-Cookie", cookie.OutputString(None)))
			
			start_response(status,
				[(tornado.escape.native_str(k), tornado.escape.native_str(v)) for (k,v) in headers])
			
			for s in handler._write_buffer:
				yield s
	
	def call2(self, request):
		"""Called by HTTPServer to execute the request."""
		transforms = [t(request) for t in self.transforms]
		handler = None
		args = []
		kwargs = {}
		handlers = self._get_host_handlers(request)
		if not handlers:
			handler = tornado.web.RedirectHandler(
				self, request, url="http://" + self.default_host + "/")
		else:
			for spec in handlers:
				match = spec.regex.match(request.path)
				if match:
					handler = spec.handler_class(self, request, **spec.kwargs)
					if spec.regex.groups:
						# None-safe wrapper around url_unescape to handle
						# unmatched optional groups correctly
						def unquote(s):
							if s is None: return s
							return tornado.escape.url_unescape(s, encoding=None)
						# Pass matched groups to the handler.  Since
						# match.groups() includes both named and unnamed groups,
						# we want to use either groups or groupdict but not both.
						# Note that args are passed as bytes so the handler can
						# decide what encoding to use.

						if spec.regex.groupindex:
							kwargs = dict(
								(k, unquote(v))
								for (k, v) in match.groupdict().iteritems())
						else:
							args = [unquote(s) for s in match.groups()]
					break
			if not handler:
				handler = tornado.web.ErrorHandler(self, request, status_code=404)

		# In debug mode, re-compile templates and reload static files on every
		# request so you don't need to restart to see changes
		if self.settings.get("debug"):
			if getattr(tornado.web.RequestHandler, "_templates", None):
				for loader in tornado.web.RequestHandler._templates.values(): #@UndefinedVariable
					loader.reset()
			tornado.web.RequestHandler._static_hashes = {}

		return (handler, transforms, args, kwargs)


class HTTPRequestGenerator(tornado.wsgi.HTTPRequest):
	def __init__(self, environ):
		"""Parses the given WSGI environ to construct the request."""
		self.method = environ["REQUEST_METHOD"]
		self.path = urllib.quote(environ.get("SCRIPT_NAME", ""))
		self.path += urllib.quote(environ.get("PATH_INFO", ""))
		self.uri = self.path
		self.arguments = {}
		self.query = environ.get("QUERY_STRING", "")
		if self.query:
			self.uri += "?" + self.query
			arguments = cgi.parse_qs(self.query)
			for name, values in arguments.iteritems():
				values = [v for v in values if v]
				if values: self.arguments[name] = values
		self.version = "HTTP/1.1"
		self.headers = tornado.httputil.HTTPHeaders()
		if environ.get("CONTENT_TYPE"):
			self.headers["Content-Type"] = environ["CONTENT_TYPE"]
		if environ.get("CONTENT_LENGTH"):
			self.headers["Content-Length"] = environ["CONTENT_LENGTH"]
		for key in environ:
			if key.startswith("HTTP_"):
				self.headers[key[5:].replace("_", "-")] = environ[key]
		self.protocol = environ["wsgi.url_scheme"]
		self.remote_ip = environ.get("REMOTE_ADDR", "")
		if environ.get("HTTP_HOST"):
			self.host = environ["HTTP_HOST"]
		else:
			self.host = environ["SERVER_NAME"]
	
	def read_body(self, environ):
		if self.headers.get("Content-Length"):
			self.body = environ["wsgi.input"].read(
				int(self.headers["Content-Length"]))
		else:
			self.body = ""
	
	def parse_request_body(self, environ, use_fieldstorage):
		self.files = {}
		content_type = self.headers.get("Content-Type", "")
		if content_type.startswith("application/x-www-form-urlencoded"):
			self.read_body(environ)
			for name, values in cgi.parse_qs(self.body).iteritems():
				self.arguments.setdefault(name, []).extend(values)
		elif content_type.startswith("multipart/form-data"):
			if 'boundary=' in content_type:
				if use_fieldstorage:
					self.files = cgi.FieldStorage(environ=environ, 
						fp=environ["wsgi.input"])
				else:
					boundary = content_type.split('boundary=',1)[1]
					if boundary:
						tornado.httputil.parse_multipart_form_data(
							tornado.escape.utf8(boundary), self.body, self.arguments, self.files)
			else:
				logging.warning("Invalid multipart/form-data")

		self._start_time = time.time()
		self._finish_time = None

class RequestHandlerGenerator(tornado.web.RequestHandler):
	USE_COROUTINE = True
	USE_FIELDSTORAGE = True
	
	def finish(self, chunk=None):
		"""Finishes this response, ending the HTTP request."""
		if self._finished:
			raise RuntimeError("finish() called twice.  May be caused "
							   "by using async operations without the "
							   "@asynchronous decorator.")

		if chunk is not None: self.write(chunk)

		# Automatically support ETags and add the Content-Length header if
		# we have not flushed any content yet.
		if not self._headers_written:
			if (self._status_code == 200 and
				self.request.method in ("GET", "HEAD") and
				"Etag" not in self._headers):
				etag = self.compute_etag()
				if etag is not None:
					inm = self.request.headers.get("If-None-Match")
					if inm and inm.find(etag) != -1:
						self._write_buffer = []
						self.set_status(304)
					else:
						self.set_header("Etag", etag)
			if "Content-Length" not in self._headers:
				content_length = sum(len(part) for part in self._write_buffer)
				self.set_header("Content-Length", content_length)

		if hasattr(self.request, "connection"):
			# Now that the request is finished, clear the callback we
			# set on the IOStream (which would otherwise prevent the
			# garbage collection of the RequestHandler when there
			# are keepalive connections)
			self.request.connection.stream.set_close_callback(None)

		self.flush(include_footers=True)
#		self.request.finish()
#		self._log()
		self._finished = True

	
	def flush(self, include_footers=False):
		chunk = tornado.util.b("").join(self._write_buffer)
		self._write_buffer = []
		if not self._headers_written:
			self._headers_written = True
			for transform in self._transforms:
				self._headers, chunk = transform.transform_first_chunk(
					self._headers, chunk, include_footers)
#			headers = self._generate_headers()
			self._write_coroutine.next()
		else:
			for transform in self._transforms:
				chunk = transform.transform_chunk(chunk, include_footers)
#			headers = tornado.util.b("")

		# Ignore the chunk and only write the headers for HEAD requests
		if self.request.method == "HEAD":
#			if headers:
#				self._write_coroutine.send(headers)
			return

		if chunk:
#			self._write_coroutine.send(headers)
			self._write_coroutine.send(chunk)

	
# END Apache License code
