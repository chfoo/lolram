# encoding=utf8

'''WSGI and HTTP application'''

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

__doctype__ = 'restructuredtext en'

__version__ = '0.1'

import gzip
import cStringIO as StringIO
import wsgiref.util
import httplib
import os
import warnings
import inspect
import sys
import imp
import traceback
import tempfile
import datetime
import mimetypes
import itertools
import runpy
try:
	runpy.run_path
except AttributeError, e:
	warnings.warn(str(e))
	from backports import runpy
import cgi

import configloader
import mylogger
import urln11n
import dataobject
import components.database
import components.session
import components.serializer
logger = mylogger.get_logger()
import routes
import pathutil
import components.wui
import components.lolramvanity
import components.staticfile
import components.cms
import components.accounts

LT = '\r\n'
HTTP_TIME_PARSE_STR = '%a, %d %b %Y %H:%M:%S %Z'
HTTP_TIME_FORMAT_STR = '%a, %d %b %Y %H:%M:%S GMT'

class WSGIApp(object):
	'''The WSGI Application'''
	
	default_config = configloader.DefaultSectionConfig('site',
		script_name='/',
	)
	
	def __init__(self, config_filename, testing=False):
		logger.info(u'Starting up')
		
		conf = configloader.load(config_filename)
		
		if conf is None:
			logger.error(u'Configuration file ‘%s’ not found', config_filename)
			return
		
		conf.populate_section(self.default_config)
		
		if not conf:
			logger.error(u'No site apps defined in ‘%s’', config_filename)
			return
		
		if not conf.site:
			logger.error(u'Missing [site] in app conf')
		
		path_ = conf.site.path
		path = os.path.abspath(path_)
			
		if path != path_ and not os.path.exists(path):
			conf_dirpath = os.path.join(os.path.dirname(config_filename),
				path_)
			logger.warning(u'Site app directory ‘%s’ does not match absolute directory ‘%s’. Falling back to ‘%s’', 
				path_, path, conf_dirpath)
			
			path = conf_dirpath
		
		if not os.path.exists(path):
			logger.error(u'Site app directory ‘%s’ does not exist', 
				path)
		
		try:
			launcher = Launcher(path, conf.site.script_name)
			self.launcher = launcher
		except:
			logger.exception(u'Unable to launch site')
			self.launcher = None
		
		self.testing = testing
	
	def __call__(self, environ, start_response):
		logger.debug(u'••••• WSGI Call •••••')
		
		if self.testing:
			logger.debug(u'Testing mode')
			wsgiref.util.setup_testing_defaults(environ)
		
		if self.launcher:
			return self.launcher(environ, start_response)
			

class Responder(object):
	'''HTTP response manager'''
	
	READ_SIZE = 4096
	
	def __init__(self, environ, start_response):
		self.environ = environ
		self.start_response = start_response
		self._headers = dataobject.HTTPHeaders()
		self.status_code = httplib.INTERNAL_SERVER_ERROR
		self.status_msg = 'Internal server error'
		self.output = []
		self.headers['content-type'] = 'text/plain'
		self.chunked = True
	
	@property
	def headers(self):
		return self._headers
	
	def set_status(self, code, msg):
		'''Set the HTTP response status code and message'''
		
		logger.debug(u'Set status %s:%s', code, msg)
		
		self.status_code = int(code)
		self.status_msg = msg
	
	def get_status(self):
		'''Get the HTTP status code and message
		
		:rtype: `tuple`
		'''
		
		return (self.status_code, self.status_msg)
	
	def ok(self):
		'''Set HTTP response status code to 200 OK'''
		self.set_status(200, 'OK')
		
	def set_output(self, iterable):
		'''Override the output with a given iterable'''
		
		self.output = iterable
	
	def set_content_type(self, s):
		'''Set the MIME type'''
		
		self.headers['content-type'] = s
		
	def output_text(self, text):
		'''Append text to the output'''
		
		self.output = itertools.chain(self.output, [text])
	
	def set_cache_time(self, max_age=31556926, scope='private'):
		'''Set the HTTP cache header'''
		
		self.headers['cache-control'] = '%s; max-age=%d' % (scope, max_age)
	
	def redirect(self, url, code=307):
		'''Do HTTP status and location for redirection'''
		
		logger.debug(u'Redirect operation %s:‘%s’', code, url)
		
		self.set_status(code, 'Redirect')
		self.headers['location'] = str(url)
		self.output_text('Redirect: ')
		self.output_text(str(url))
		self.redirect_flag = True
		
	def set_content_type(self, s):
		'''Set HTTP MIME content time'''
		
		self.headers['content-type'] = s
	
	def set_chunked_transfer(self, enabled=True):
		'''Enabled chunked transfer encoding rather than computing length'''
		
		self.chunked = enabled
	
	def output_file(self, path, download_filename=None):
		'''Return iterator for a file from the filesystem'''
		
		self.headers['X-Sendfile'] = path
		
		last_modified = datetime.datetime.utcfromtimestamp(
			os.path.getmtime(path))
		
		mt = mimetypes.guess_type(path)
		
		if mt:
			self.headers['content-type'] = mt[0]
		else:
			del self.headers['content-type']
		
		logger.debug(u'Output file ‘%s’→‘%s’', path, download_filename)
		
		# Need 1 second precision (in case filesystems that support 
		# microseconds since we only transmit 1 second precision
		# Otherwise, we get a bug comparing dates
		last_modified = last_modified.replace(
			last_modified.year,
			last_modified.month,
			last_modified.day,
			last_modified.hour,
			last_modified.minute,
			last_modified.second,
			0
		)
		
		if_modified_since = self.environ.get('HTTP_IF_MODIFIED_SINCE')
		if if_modified_since:
			if_modified_since = datetime.datetime.strptime(
				if_modified_since, HTTP_TIME_PARSE_STR)
		
			# 304 not modified feature
			if last_modified <= if_modified_since:
				logger.debug(u'Not modified')
				self.set_status(304, 'Not modified')
				del self.headers['content-type']
				return []
		
		self.headers['accept-ranges'] = 'bytes'
		self.headers['last-modified'] = last_modified.strftime(
			HTTP_TIME_FORMAT_STR)
		
		if download_filename:
			self.headers['content-disposition'] = \
				u'attachment; filename=%s' % download_filename
		
		# There is a request for a partial file
		http_range = self.environ.get('HTTP_RANGE')
		if http_range and 'bytes' in http_range:
			range_type, range_value = http_range.split('=')
			range_lower, range_upper = map(int, range_value.split('-'))
		else:
			range_lower = 0
			range_upper = os.path.getsize(path)
		
		range_size = range_upper - range_lower
		
		self.headers['content-length'] = str(range_size)
		
		logger.debug(u'Range: %s→%s', range_lower, range_upper)
		def f():
			bytes_left = range_size
			with open(path, 'rb') as f_obj:
				f_obj.seek(range_lower)
			
				while True:
					bytes_left = max(0, bytes_left)
					logger.debug(u'Bytes left: %s', bytes_left)
					data = f_obj.read(min(bytes_left, self.READ_SIZE))
				
					if data == '':
						break
				
					bytes_left -= self.READ_SIZE
					yield data
			
		return f()
		
	def pre_respond(self):
		'''Trigger generator function execution a bit early 
		so things are set correctly'''
		
		logger.debug(u'Pre-respond!')
		
		iterable = self.output
		try:
			iterable_1 = next(iterable)
			iterable_temp = iterable
			
			def f():
				yield iterable_1
				
				try:
					while True:
						yield next(iterable_temp)
				except StopIteration:
					pass
			
			iterable = f()
			self.output = iterable
			
		except TypeError, e:
			logger.debug(e)
	
	def respond(self):
		'''Start a WSGI response and return an iterable response body
		
		:rtype: `iter`
		'''
		
		logger.debug(u'Respond %s:%s', self.status_code, self.status_msg)
		
		iterable = self.output
		
		# chunked transfer is disabled in compliance with WSGI
		if self.chunked and False: 
			logger.debug(u'Chunked transfer encoding')
			self.headers['transfer-encoding'] = 'chunked'
			iterable = chunked(iterable)
		
		if 'accept-encoding' in self.headers \
		and self.headers['accept-encoding'].find('gzip') != -1 \
		and 'content-type' in self.headers \
		and self.headers['content-type'].startswith('text'):
			# If the MIME type is text-like, then we can probably compress 
			# it
			self.headers['content-encoding'] = 'gzip'
			if 'content-size' in self.headers:
				del self.headers['content-size']
			iterable = compress(iterable)
		
		if not self.chunked:
			temp_file = tempfile.SpooledTemporaryFile(10240)
			map(temp_file.write, iterable)
			self.headers['content-size'] = str(temp_file.tell())
			temp_file.seek(0)
			iterable = wsgiref.util.FileWrapper(temp_file)
		
		
		status = '%s %s' % (self.status_code, 
			self.status_msg or self.status_code)
		
		logger.debug(u'Start response')
#		logger.debug(u'Headers: %s', self.headers.items())

		self.start_response(status, self.headers.items())
		
		for v in iterable:
			logger.debug(u'Yield size: %s', len(v))
#			logger.debug(u'Data: %s', repr(v))
			yield v
		

class BufferFile(object):
	'''File-like, read-once buffer for adapting to generators'''
	
	def __init__(self):
		self.buffer = StringIO.StringIO()
	
	def write(self, data):
		self.buffer.write(data)
	
	def read(self):
		self.buffer_old = self.buffer
		self.buffer = StringIO.StringIO()
		self.buffer_old.seek(0)
		return self.buffer_old.read()
		
class Launcher(object):
	def __init__(self, dirpath, script_name):
		script_name = urln11n.collapse_path(script_name)
		path = os.path.join(dirpath, 'code')
#		globals_dict = runpy.run_path(path)
		self.app = None
		
		# FIXME: runpy tries to restore state which means imports done
		# by the application will be None
		# Instead we'll just import it
		f, n, d = imp.find_module('__main__', [path])
		sys.path.append(path)
		m = imp.load_module('m', f, n, d)
		globals_dict = m.__dict__
		
		logger.debug(u'Launching ‘%s’‘%s’', path, script_name)
		
		for key, value in globals_dict.iteritems():
			logger.debug(u'Search for callable: %s', key)
			if inspect.isclass(value) and '__call__' in dir(value):
				self.app = value(dirpath, script_name)
				break
		
		if not self.app:
			logger.error(u'Unable to launch site app')
			logger.error(u'Ensure that __main__.py exists')
		
		self.script_name = script_name
		if script_name:
			self.shift_count = len(script_name.split('/'))
		else:
			self.shift_count = 0
	
	def __call__(self, environ, start_response):
		logger.debug(u'Shifting %s', self.shift_count)
		for i in xrange(self.shift_count):
			wsgiref.util.shift_path_info(environ)
		return self.app(environ, start_response)

class SiteApp(object):
	default_config = configloader.DefaultSectionConfig('site',
		create_missing_dirs=True,
		debugging_tracebacks=True,
	)
	default_components = [
		components.staticfile.StaticFileManager,
		components.database.DatabaseManager, 
		components.session.SessionManager,
		components.serializer.SerializerManager,
		components.accounts.AccountsManager,
		components.cms.CMSManager,
		components.wui.WUIManager,
		components.lolramvanity.LolramVanityMgr,
	]
	
	# TODO: object pooling
	
	def __init__(self, dirpath, script_name):
		self._function_router = routes.Router()
		self._dirs = dataobject.DirInfo(dirpath)
		self._confname = os.path.join(dirpath, 'site.conf')
		self._conf = configloader.load(self._confname)
		
		if self._conf is None:
			logger.error(u'Site configuration ‘%s’ not found', self._confname)
			return
		
		self._conf.populate_section(self.default_config)
		
		if self._conf.site and self._conf.site.create_missing_dirs:
			self.create_dirs()
		
		self._component_manager_dict = dataobject.DataObject()
		self._component_manager_list = []
		
		fardel = self.make_fardel()
		self.init_component_managers(fardel)
		self.init(fardel)
		
	def init_component_managers(self, fardel):
		
		for class_ in self.default_components:
			logger.info(u'Initializing component ‘%s’ as ‘%s’', 
				class_.__name__, class_.name)
				
			if class_.default_config:
				self._conf.populate_section(class_.default_config)
				
			component_manager = class_(fardel)
			self._component_manager_list.append(component_manager)
			self._component_manager_dict[class_.name] = component_manager
	
	def init(self):
		pass

	def create_dirs(self):
		logger.debug(u'Create dirs')
		for dirname in (self.dirs.code, self.dirs.www, self.dirs.var,
		self.dirs.db, self.dirs.upload):
			if not os.path.exists(dirname):
				logger.debug(u'Directory ‘%s’ does not exist, creating.',
					dirname)
				os.mkdir(dirname)
	
	def __call__(self, environ, start_response):
		logger.debug(u'Call')
		
		responder = Responder(environ, start_response)
		recon_url = pathutil.request_uri(environ)
		url = urln11n.URL(recon_url)
		request_headers = dataobject.HTTPHeaders(environ=environ)
		path_list = urln11n.collapse_path(environ['PATH_INFO']).split('/')
		
		controller = None
		args = []
		
		if path_list:
			controller = path_list[0]
			args = path_list[1:]
		
		request_info = dataobject.RequestInfo(
			headers=request_headers,
			script_name=environ['SCRIPT_NAME'],
			path_info=environ['PATH_INFO'],
			url=url,
			script_path=urln11n.collapse_path(environ['SCRIPT_NAME']),
			local_path=urln11n.collapse_path(environ['PATH_INFO']),
			controller=controller,
			args=args,
			form=cgi.FieldStorage(fp=environ['wsgi.input'], 
				environ=environ, keep_blank_values=True),
		)
		component_agent_list = []
		component_agent_dict = dataobject.DataObject()
		fardel = self.make_fardel(request=request_info, response=responder,
			data=dataobject.DataObject(), 
			component_agents=component_agent_dict)
			
		for manager in self._component_manager_list:
			if manager.agent_class:
				agent = manager.agent_class(fardel, manager)
				component_agent_dict[manager.name] = agent
				component_agent_list.append(agent)
		
#		logger.debug(environ)
		logger.debug(u'Reconstructed URL: %s', url)
		
		iterable = None
		
		try:
			for c in component_agent_list:
				logger.debug(u'Component agent ‘%s’ setup', c.__class__.__name__)
				c.setup(fardel)
			
			self.setup(fardel)
			
			for c in component_agent_list:
				logger.debug(u'Component agent ‘%s’ control', c.__class__.__name__)
				
				iterable = c.control(fardel)
				
				if iterable is not None:
					break
			
			if iterable is None:
				function = self.router.get(fardel.req.path)
				
				if function:
					logger.debug(u'Got router serve ‘%s’', function)
					iterable = function(fardel)
			
			if iterable is None:
				for c in component_agent_list:
					logger.debug(u'Component agent ‘%s’ render', c.__class__.__name__)
					iterable = c.render(fardel)
				
					if iterable is not None:
						break
			
			if iterable is not None:
				responder.set_output(iterable)
				responder.pre_respond()
			
			self.cleanup(fardel)
			
			for c in reversed(component_agent_list):
				logger.debug(u'Component agent ‘%s’ cleanup', c.__class__.__name__)
				c.cleanup(fardel)
			
		except Exception, e:
			if fardel.conf.site.debugging_tracebacks: 
				logger.exception(u'Site app error ‘%s’', e)
			
			responder.set_status(500, 'Internal server error')
			
			tb_text = traceback.format_exc()
			exc_info = sys.exc_info()
			
			try:
				tb_text = cgitb.text(exc_info)
			except:
				pass
			
			if fardel.conf.site.debugging_tracebacks:
				try:
					self.do_traceback_error_page(fardel, exc_info)
				except:
					self.do_simple_error_page(fardel, tb_text)
			else:
				self.do_simple_error_page(fardel, 'A system error has occured')
		
		return responder.respond()
	
	def make_fardel(self, **kargs):
		fardel = dataobject.Fardel(
			config=self.conf, 
			dirs=self.dirs,
			component_managers=self._component_manager_dict, 
			**kargs)
		return fardel
	
	def do_simple_error_page(self, fardel, msg=''):
		'''Set a simple error page in the responder'''
		
		responder = fardel.resp
		# A page larger than 1 KB will show in the browser
		responder.set_content_type('text/html')
		responder.output_text('<html><body>')
		responder.output_text('<h1>%s %s</h1>' % responder.get_status())
		responder.output_text('<pre>')
		responder.output_text(msg.encode('utf8'))
		responder.output_text('</pre>')
		responder.output_text('</body>')
		responder.output_text('<!--')
		responder.output_text('there is no spoon 528491 ' * 42)
		responder.output_text('-->')
		responder.output_text('</html>')
	
	def do_traceback_error_page(self, fardel, exc_info=None):
		'''Set a detailed trackback error page in the responder'''
		
		if exc_info is None:
			exc_info = sys.exc_info()
		
		responder = fardel.response
		responder.set_content_type('text/html')
		responder.output_text('<html><body>')
		responder.output_text('<h1>%s %s</h1>' % responder.get_status())
		responder.output_text(cgitb.html(exc_info))
		responder.output_text('</body></html>')
	
	def setup(self, fardel):
		pass
	
	def cleanup(self, fardel):
		pass
	
	@property
	def router(self):
		return self._function_router
	
	@property
	def component_router(self):
		return self._component_router
	
	@property
	def dirs(self):
		return self._dirs
	
	@property
	def conf(self):
		return self._conf
	
	@property
	def script_name(self):
		return self._script_name
	
	@property
	def component_managers(self):
		return self._component_manager_dict

def compress(values):
	file_obj = BufferFile()
	compress_obj = gzip.GzipFile(mode='wb', fileobj=file_obj)
	
	for value in values:
		compress_obj.write(value)
		yield file_obj.read()
	
	compress_obj.close()
	yield file_obj.read()

def chunked(values):
	for value in values:
		yield '%X' % len(value)
		yield LT
		yield value
		yield LT
	
	yield '0'
	yield LT

