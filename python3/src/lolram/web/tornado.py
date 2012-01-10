'''Tornado WSGI adapters/replacements'''
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
#
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
#
from tornado import httputil, escape
from tornado.escape import utf8, native_str
from tornado.web import RedirectHandler, ErrorHandler, RequestHandler
import cgi
import http.client
import logging
import time
import tornado.web
import tornado.wsgi
import urllib

__docformat__ = 'restructedtext en'

SIZE_BYTES_1MB = '1048576'

class WSGIApplication(tornado.web.Application):
	def __call__(self, environ, start_response):
		request = HTTPRequest(environ)
		transforms = self._apply_transforms(request)
		
		handler, args, kwargs = self._get_handler_and_args_for_request(request)
		request.set_handler_and_response_fn(handler, start_response)
		
		handler._execute(transforms, *args, **kwargs)
		assert handler._finished
		
		return []
	
	def _apply_transforms(self, request):
		return [t(request) for t in self.transforms]
	
	def _get_handler_and_args_for_request(self, request):
		handler = None
		args = []
		kwargs = {}
		handlers = self._get_host_handlers(request)
		if not handlers:
			handler = RedirectHandler(
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
							return escape.url_unescape(s, encoding=None)
						# Pass matched groups to the handler.  Since
						# match.groups() includes both named and unnamed groups,
						# we want to use either groups or groupdict but not both.
						# Note that args are passed as bytes so the handler can
						# decide what encoding to use.

						if spec.regex.groupindex:
							kwargs = dict(
								(k, unquote(v))
								for (k, v) in match.groupdict().items())
						else:
							args = [unquote(s) for s in match.groups()]
					break
			if not handler:
				handler = ErrorHandler(self, request, status_code=404)

		# In debug mode, re-compile templates and reload static files on every
		# request so you don't need to restart to see changes
		if self.settings.get("debug"):
			self._reload_templates()

		return handler, args, kwargs
	
	def _reload_templates(self):
		if getattr(RequestHandler, "_templates", None):
			for loader in list(RequestHandler._templates.values()): #@UndefinedVariable
				loader.reset()
		RequestHandler._static_hashes = {}


class MaxFileSizeInMemoryError(Exception):
	def __init__(self, msg='custom_message'):
		if msg == 'custom_message':
			Exception.__init__(self, 'Safe file size in memory reached. '
				'Perhaps you should use field storage and file objects instead')
		else:
			Exception.__init__(self, msg)
		

class HTTPRequest(tornado.wsgi.HTTPRequest):
	def __init__(self, environ):
		self._environ = environ
		self._start_time = time.time()
		self._finish_time = None
		self._started = False
		
		self._parse_environ()
		self._parse_request_field_storage()
	
	@property
	def environ(self):
		return self._environ
	
	@property
	def body(self):
		if not hasattr(self, '_body'):
			self._read_request_body()
		
		return self._body
	
	@property
	def field_storage(self):
		return self._field_storage
	
	@property
	def files(self):
		if not hasattr(self, '_files'):
			self._parse_request_body()
		
		return self._files
	
	def _parse_environ(self):
		environ = self.environ
		self.method = environ["REQUEST_METHOD"]
		self.path = urllib.parse.quote(environ.get("SCRIPT_NAME", ""))
		self.path += urllib.parse.quote(environ.get("PATH_INFO", ""))
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
		self.headers = httputil.HTTPHeaders()
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
	
	def _read_request_body(self, safeFileSize=SIZE_BYTES_1MB):
		content_length = int(self.headers.get("Content-Length", 0))
		
		if content_length:
			if safeFileSize and content_length >= safeFileSize:
				raise MaxFileSizeInMemoryError()
			
			self._body = self.environ["wsgi.input"].read(content_length)
		else:
			self._body = ""
			
	def _parse_request_body(self):
		self._files = {}
		content_type = self.headers.get("Content-Type", "")
		if content_type.startswith("application/x-www-form-urlencoded"):
			for name, values in cgi.parse_qs(self.body).iteritems():
				self.arguments.setdefault(name, []).extend(values)
		elif content_type.startswith("multipart/form-data"):
			if 'boundary=' in content_type:
				boundary = content_type.split('boundary=',1)[1]
				if boundary:
					httputil.parse_multipart_form_data(
						utf8(boundary), self._body, self.arguments, self._files)
			else:
				logging.warning("Invalid multipart/form-data")
	
	def _parse_request_field_storage(self):
		self._field_storage = cgi.FieldStorage(environ=self._environ, 
			fp=self._environ["wsgi.input"])

	def write(self, chunk, callback=None):
		"""Writes the given chunk to the response stream."""
		assert isinstance(chunk, tornado.util.bytes_type)
		
		if not self._started:
			self._start_response()
		
		# TODO: Use greenlets so that generators are used instead
		self._write_callable.write(chunk)
		callback()

	def finish(self):
		"""Finishes this HTTP request on the open connection."""
		
		if not self._started:
			self._start_response()
		
		self._finish_time = time.time()
	
	def set_handler_and_response_fn(self, handler, start_response):
		self._handler = handler
		self._start_response = start_response
		self._write_callable = None
	
	def _start_response(self):
		status = str(self._handler._status_code) + " " + \
		http.client.responses[self._handler._status_code]
		headers = list(self._handler._headers.items())
		
		for cookie_dict in getattr(self._handler, "_new_cookies", []):
			for cookie in list(cookie_dict.values()):
				headers.append(("Set-Cookie", cookie.OutputString(None)))
		
		self._write_callable = self._start_response(status,
			[(native_str(k), native_str(v)) for (k,v) in headers])
		