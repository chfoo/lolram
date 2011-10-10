# encoding=utf8

'''Data objects'''

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


__docformat__ = 'restructuredtext en'

import os.path
import UserDict
import cStringIO
import string
import itertools
import copy
import collections

from lolram2 import urln11n
import models
import views

from models import BaseModel
from views import BaseView

class ProtectedAttributeError(AttributeError):
	__slots__ = ()
	pass

class ProtectedObject(object):
	'''Emulates protected member class object pattern'''
	
	def __getattr__(self, k):
		if k in self.__dict__ and not k.startswith('_'):
			raise ProtectedAttributeError(u'Member ‘%s’ is not accessible' % k)
		else:
			for class_ in itertools.chain((self.__class__,), self.__class__.__bases__):
				if isinstance(class_.__dict__.get(k), property) \
				and class_.__dict__[k].fget:
					class_.__dict__[k].fget(self)
					return
			
			return self.__dict__[k]
	
	def __delattr__(self, k):
		raise ProtectedAttributeError(u'Member ‘%s’ is not accessible' % k)
	
	def __setattr__(self, k, v):
		for class_ in itertools.chain((self.__class__,), self.__class__.__bases__):
			if isinstance(class_.__dict__.get(k), property) \
			and class_.__dict__[k].fset:
				class_.__dict__[k].fset(self, v)
				return
			
		if not k.startswith('_'):
			raise ProtectedAttributeError(u'Member ‘%s’ is not accessible' % k)
		else:
			self.__dict__[k] = v

class Context(ProtectedObject):
	'''Provides context information about the current request and response'''
	
	def __init__(self, id=None, request=None, 
	response=None, environ=None, config=None, dirinfo=None, logger=None,
	is_testing=None, master=None):
		self._context_aware_instances = {}
		self._id = id
		self._request = request
		self._response = response
		self._environ = environ
		self._config = config
		self._dirinfo = dirinfo
		self._logger = logger
		self._errors = []
		self._is_testing = is_testing
		self._global_context = master
	
	@property
	def global_context(self):
		return self._global_context
	
	@property
	def master(self):
		return self._global_context
	
	@property
	def is_master(self):
		return self._global_context == self 
	
	def get_instance(self, class_, singleton=False):
		'''Get a context aware instance
		
		:rtype: `ContextAware`
		'''
		
		if singleton:
			d = self._global_context._context_aware_instances
		else:
			d = self._context_aware_instances
		
		if class_ not in d:
			assert issubclass(class_, ContextAware)
			instance = class_.__new__(class_, context_checked=True, context=self)
			instance.__init__(context_checked=True, context=self)
			instance.set_context(self)
			d[class_] = instance
		
		return d[class_]
	
	def exists(self, class_):
		return class_ in self._context_aware_instances
	
	@property
	def id(self):
		return self._id
	
	@property
	def request(self):
		'''Get `RequestInfo`
		
		:rtype: `RequestInfo`
		'''
		
		return self._request
	
	@property
	def response(self):
		'''Get `Responder`
		
		:rtype: `Responder`
		'''
		
		return self._response
	
	@property
	def environ(self):
		'''Get environment information
		
		:rtype: `dict`
		'''
		
		return self._environ
	
	@property
	def config(self):
		'''Get site configuration
		
		:rtype: `DataObject
		'''
		
		return self._config
	
	@property
	def dirinfo(self):
		'''Get `DirInfo`
		
		:rtype: `DirInfo`
		'''
		
		return self._dirinfo
	
	@property
	def logger(self):
		return self._logger
	
	@property
	def errors(self):
		'''Get list of error strings
		
		:rtype: `list`
		'''
		
		return self._errors
	
	def norm_url(self, url):
		'''Append the SCRIPT_INFO path to the URL instance
		
		:parameters:
			url : `URL`
				The URL instance
		'''
		
		if self._request.script_path:
			url.path = '%s/%s' % (self._request.script_path, url.path)

	def make_url(self, path=None, fill_path=False, 
	controller=None, fill_controller=False,
	args=None, fill_args=False,
	params=None, fill_params=False,
	query=None, fill_query=False, fill_host=False):
		'''Build a URL instance
		
		:rtype: `URL`
		'''
	
		url = urln11n.URL()
		
		if fill_host:
			url.hostname = self._request.url.hostname
			url.scheme = self._request.url.scheme
			url.port = self._request.url.port
		
		if path:
			url.path = path
		elif fill_path:
			url.path = self._request.path
		
		path_parts = []
		if controller:
			path_parts.append(controller)
		elif args or fill_args or fill_controller:
			path_parts.append(self._request.controller)
		
		if args:
			path_parts.extend(args)
		elif fill_args:
			path_parts.extend(self._request.args)
			
		if path_parts:
			url.path = '/'.join(path_parts)
		
		if params is not None:
			url.params = params
		elif fill_params:
			url.params = self._request.params
		
		if fill_query:
			url.query.update(self._request.query)
		if query is not None:
			url.query.update(query)
		
		self.norm_url(url)
		return url
	
	def str_url(self, *args, **kargs):
		'''The same as `build_url` but returns a string instead
		
		:see: `build_url`
		
		:rtype: `str`
		'''
		
		return str(self.make_url(*args, **kargs)) or '/'
	
	def page_info(self, limit=10, all=None, more=False):
		'''Compute pagination information
		
		:rtype:	`PageInfo`
		'''
		page = max(1, int(self.request.query.getfirst('page', 0)))
		offset = (page - 1) * limit
		page_min = 1
		page_max = None
		
		if all is not None:
			page_max = all // limit + 1
		
		return PageInfo(offset=offset, limit=limit, all=all, page=page, 
			page_min=page_min, page_max=page_max, more=more)
		
	@property
	def is_testing(self):
		return self._is_testing

class ContextAwareInitError(Exception):
	__slots__ = ()
	pass


class ContextAwareType(type):
	def __call__(self, context):
		return context.get_instance(self)


class ContextAware(object):
	'''Base class for classes which bind to a context'''
	
	__metaclass__ = ContextAwareType
	
	def __init__(self, context=None, context_checked=False):
		self._context = context
		if not context_checked:
			raise ContextAwareInitError(u'Context aware classes must by '
				+ 'initalized by a context instance. '
				+ 'Use context.get_context(Class)')
	
	def set_context(self, context):
		self._context = context
	
	@property
	def context(self):
		'''Get the `Context`
		
		:rtype: `Context`
		'''
		
		return self._context
	

class _SelfProxy(object):
	def __init__(self, target):
		def __getattr__(self, k):
			return target.__dict__[k]
	
		def __setattr__(self, k, v):
			target.__dict__[k] = v
	
		def __delattr__(self, k):
			del target.__dict__[k]
	
		self.__delattr__ = __delattr__
		self.__getattr__ = __getattr__
		self.__setattr__ = __setattr__


class DataObject(dict):
	'''A dictionary which properties can be accessed using dot notation
	
	:ivars:
		__ 
			This variable is a instance which will not affect the underlying
			dict instance.
	'''
	
	def __init__(self, *args, **kargs):
		'''
		
		:parameters:
			__raises_key_error : `bool`
				If `True`, then raise `KeyError` if key is not found. Otherwise,
				return `None`.
		'''
		self.__ = _SelfProxy(self)
		self.__.raises_key_error = kargs.get('__raises_key_error', False)
		if '__raises_key_error' in kargs:
			del kargs['__raises_key_error']
			
		dict.__init__(self, *args, **kargs)
	
	def __setattr__(self, k, v):
		if not k.startswith('__'):
			self[k] = v
		else:
			self.__dict__[k] = v

	def __delattr__(self, k):
		if k in self and not k.startswith('__'):
			del self[k]
		elif k in self.__dict__:
			del self.__dict__[k]

	def __getattr__(self, k):
		if not k.startswith('__'):
			if self.__.raises_key_error:
				return self[k]
			else:
				return self.get(k)
		else:
			return self.__dict__[k]

class BaseMVC(ContextAware):
	'''Base MVC class
	
	:cvar:
		default_config : `DefaultConfig`
			Default configuration values
	'''
	
	__slots__ = ()
	default_config = None
	
	@property
	def singleton(self):
		return self.master
	
	@property
	def master(self):
		return self.__class__(self.context.master)
	
	def init(self):
		'''Master instance operations'''
		pass
	
	def setup(self):
		'''Prepare for a request'''
		
		pass
	
	def control(self):
		'''Perform operations to models'''
		
		pass
	
	def render(self):
		'''Return views from models'''
		
		pass
	
	def cleanup(self):
		'''Operations after a response has been prepared'''
		
		pass
	
	def run_maintenance(self):
		'''Perform long running tasks and maintenance operations'''
		pass


class DirInfo(ProtectedObject):
	'''Disk directory paths'''
	
	__slots__ = ('_app', '_code', '_www', '_db', '_upload')
	
	def __init__(self, app, code='code', www='www', var='var', db='db',
	upload='upload'):
		self._app = os.path.abspath(app)
		self._code = os.path.join(self.app, code)
		self._www = os.path.join(self.app, www)
		self._var = os.path.join(self.app, var)
		self._db = os.path.join(self.app, db)
		self._upload = os.path.join(self.app, upload)
	
	@property
	def app(self):
		'''The path of the site directory which holds everything'''
		
		return self._app
	
	@property
	def code(self):
		'''The path of ``code`` directory'''
		
		return self._code
	
	@property
	def www(self):
		'''The path of the ``www`` directory'''
		
		return self._www
	
	@property
	def var(self):
		'''The path of the ``var`` directory'''
		
		return self._var
	
	@property
	def db(self):
		'''The path of the ``db`` directory'''
		
		return self._db
	
	@property
	def upload(self):
		'''The path of the ``upload`` directory'''
		
		return self._upload 


class RequestInfo(ProtectedObject):
	'''Information about the current request'''
	
	__slots__ = ('_script_name', '_path_info', '_args', '_form', '_url',
		'_headers', '_controller', '_local_path', '_script_path',)
	
	def __init__(self, script_name=None, path_info=None, args=None,
	form=None, url=None, headers=None, controller=None, script_path=None,
	local_path=None, is_post=None):
		self._script_name = script_name
		self._path_info = path_info
		self._args = args
		self._form = form
		self._url = url
		self._headers = headers
		self._controller = controller
		self._local_path = local_path
		self._script_path = script_path
		self._is_post = is_post
	
	@property
	def args(self):
		'''The arguments passed to the controller
		
		:rtype: `list`
		'''
		
		return self._args
	
	@property
	def script_name(self):
		'''The value of the environment variable ``SCRIPT_NAME``
		
		:rtype: `str`
		'''
		
		return self._script_name
	
	@property
	def path_info(self):
		'''The value of the environment variable ``PATH_INFO``
		
		:rtype: `str`
		'''
		
		return self._path_info
	
	@property
	def path(self):
		'''The URL path in which the site application is concerned about
		
		:rtype: `str`
		'''
		
		return self._local_path
	
	@property
	def script_path(self):
		'''The base URL path in which the site application is running under
		
		:rtype: `str`
		'''
		
		return self._script_path
	
	@property
	def form(self):
		'''HTTP POST request
		
		:rtype: `cgi.FieldStorage`
		'''
		
		return self._form
	
	@property
	def url(self):
		'''The URL instance
		
		:rtype: `URL`
		'''
		
		return self._url
	
	@property
	def headers(self):
		'''The request HTTP headers
		
		:rtype: `HTTPHeaders`
		'''
		
		return self._headers
	
	@property
	def full_path(self):
		'''The full path of the URL
		
		:rtype: `str`
		'''
		
		return self._url.path
	
	@property
	def params(self):
		'''The parameters portion of the URL
		
		:rtype: `str`
		'''
		
		return self._url.params
	
	@property
	def query(self):
		'''The HTTP GET query 
		
		:rtype: `URLQuery`
		'''
		
		return self._url.query
	
	@property
	def controller(self):
		'''The name of the controller
		
		:rtype: `str`
		'''
		
		return self._controller
	
	@property
	def is_post(self):
		return self._is_post
	


class URL(urln11n.URL, ProtectedObject):
	__slots__ = ()
	
	def __init__(self, *args, **kargs):
		urln11n.URL.__init__(self, *args, **kargs)
		ProtectedObject.__init__(self)


class MVPair(collections.namedtuple('MVPair', ['model', 'view', 'opts']),
models.BaseModel):
	'''Return a named tuple to be used for view rendering
	
	:rtype: `MVPair`
	'''
	
	__slots__ = ()
	
	def __new__(cls, model, view=None, **opts):
		
		assert isinstance(model, models.BaseModel)
		
		if view:
			assert issubclass(view, views.BaseView)
		else:
			assert issubclass(model.default_renderer, views.BaseView)
		
		return super(MVPair, cls).__new__(cls, model, view, opts)

	
	def render(self, context, format, **opts):
		opts.update(self.opts)
		
		if not self.view:
			view = self.model.default_renderer
		else:
			view = self.view
		
		return view.render(context, self.model, format, **opts)
	

#class PageInfo(collections.namedtuple('PageInfo', 
#['offset', 'limit', 'all', 'more', 'page', 'page_min', 'page_max']),
#BaseModel):
#	__slots__ = ()

class PageInfo(models.BaseModel):
	def __init__(self, offset=None, limit=50, all=None, more=None, page=None,
	page_min=None, page_max=None):
		self.offset = offset
		self.limit = limit
		self.all = all
		self.more = more
		self.page = page
		self.page_min = page_min
		self.page_max = page_max

