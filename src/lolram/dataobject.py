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


__doctype__ = 'restructuredtext en'

import os.path
import UserDict
import cStringIO
import string
import urln11n

class ProtectedAttributeError(AttributeError):
	pass

class ProtectedObject(object):
	'''Emulates protected member class object pattern'''
	
	def __getattr__(self, k):
		if not k.startswith('_'):
			raise ProtectedAttributeError(u'Member ‘%s’ is not accessible' % k)
		else:
			return self.__dict__[k]
	
	def __delattr__(self, k):
		raise ProtectedAttributeError(u'Member ‘%s’ is not accessible' % k)
	
	def __setattr__(self, k, v):
		for class_ in self.__class__.__bases__:
			if isinstance(class_.__dict__.get(k), property):
				class_.__dict__[k].setter(v)
				return
			
		if not k.startswith('_'):
			raise ProtectedAttributeError(u'Member ‘%s’ is not accessible' % k)
		else:
			self.__dict__[k] = v

class Context(ProtectedObject):
	def __init__(self, singleton_instances=None, id=None, request=None, 
	response=None, environ=None, config=None, dirinfo=None, logger=None,):
		self._context_aware_instances = {}
		self._singleton_instances = singleton_instances
		self._id = id
		self._request = request
		self._response = response
		self._environ = environ
		self._config = config
		self._dirinfo = dirinfo
		self._logger = logger
	
	def get_instance(self, class_, singleton=False):
		if singleton:
			d = self._singleton_instances 
		else:
			d = self._context_aware_instances
		
		if class_ not in d:
			assert issubclass(class_, ContextAware)
			instance = class_(context_checked=True, context=self)
			instance.set_context(self)
			d[class_] = instance
		
		return d[class_]
	
	@property
	def id(self):
		return self._id
	
	@property
	def request(self):
		return self._request
	
	@property
	def response(self):
		return self._response
	
	@property
	def environ(self):
		return self._environ
	
	@property
	def config(self):
		return self._config
	
	@property
	def dirinfo(self):
		return self._dirinfo
	
	@property
	def logger(self):
		return self._logger

class ContextAwareInitError(Exception):
	pass

class ContextAware(object):
	def __init__(self, context_checked=False, context=None):
		self._context = context
		if not context_checked:
			raise ContextAwareInitError(u'Context aware classes must by '
				+ 'initalized by a context instance. '
				+ 'Use context.get_context(Class)')
	
	def set_context(self, context):
		self._context = context
	
	@property
	def context(self):
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
	default_config = None
	
	@property
	def singleton(self):
		return self.context.get_instance(self.__class__, singleton=True)
	
	def init(self):
		pass
	
	def setup(self):
		pass
	
	def control(self):
		pass
	
	def render(self):
		pass
	
	def cleanup(self):
		pass

class BaseRenderer(object):
	@staticmethod
	def supports(format):
		return 'to_%s' in dir(Renderer)
	
	@staticmethod
	def render(context, model, format='html'):
		return Renderer.__dict__['to_%s' % format](context, model)
	
class BaseModel(object):
	renderer = NotImplemented
	

class DirInfo(ProtectedObject):
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
		return self._app
	
	@property
	def code(self):
		return self._code
	
	@property
	def www(self):
		return self._www
	
	@property
	def var(self):
		return self._var
	
	@property
	def db(self):
		return self._db
	
	@property
	def upload(self):
		return self._upload 

class RequestInfo(ProtectedObject):
	def __init__(self, script_name=None, path_info=None, args=None,
	form=None, url=None, headers=None, controller=None, script_path=None,
	local_path=None):
		self._script_name = script_name
		self._path_info = path_info
		self._args = args
		self._form = form
		self._url = url
		self._headers = headers
		self._controller = controller
		self._local_path = local_path
		self._script_path = script_path
	
	@property
	def args(self):
		return self._args
	
	@property
	def script_name(self):
		return self._script_name
	
	@property
	def path_info(self):
		return self._path_info
	
	@property
	def path(self):
		return self._local_path
	
	@property
	def script_path(self):
		return self._script_path
	
	@property
	def form(self):
		return self._form
	
	@property
	def url(self):
		return self._url
	
	@property
	def headers(self):
		return self._headers
	
	@property
	def full_path(self):
		return self._url.path
	
	@property
	def params(self):
		return self._url.params
	
	@property
	def query(self):
		return self._url.query
	
	@property
	def controller(self):
		return self._controller
	
class HTTPHeaders(UserDict.DictMixin):
	def __init__(self, environ=None, read_only=False):
		self.data = {}
		self.read_only = False
	
		if environ is not None:
			for key, value in environ.iteritems():
				if key.startswith('HTTP_'):
					name = key.replace('HTTP_', '', 1)
					header = self.parse_header(name, value)
					self.add_header(header)
		
		self.read_only = read_only
	
	def _check_read_only(self):
		if self.read_only:
			raise AttributeError('Read-only')
					
	def __getitem__(self, name):
		return str(self.data[normalize_header_name(name)][0])
	
	def __setitem__(self, name, value):
		self._check_read_only()
		self.data[normalize_header_name(name)] = [self.parse_header(name, value)]
	
	def __delitem__(self, name):
		self._check_read_only()		
		del self.data[normalize_header_name(name)]
	
	def __contains__(self, name):
		return normalize_header_name(name) in self.data
	
	def __iter__(self):
		return iter(self.data)
	
	def get_list(self, name, default=None):
		return self.data.get(normalize_header_name(name), default)
	
	def get_first(self, name, default=None):
		v = self.data.get(normalize_header_name(name), default)
		if isinstance(v, list):
			return v[0]
		else:
			return v
	
	def add(self, name, value, **params):
		self.add_header(HTTPHeader(name, value, **params))
	
	def add_header(self, header):
		self._check_read_only()
		if header.name not in self.data:
			self.data[header.name] = []
		
		self.data[header.name].append(header)
	
	def parse_header(self, name, value):
		header = HTTPHeader(name)
		
		if value.find(';') != -1:
			header.value, sep, vl = value.partition(',')
		
			for i in vl.split(';'):
				k, sep, v = i.partition('=')
				k = k.strip()
				v = v.strip()
			
				if k:
					header.params[k] = v
		
		else:
			header.value = value
		
		return header
	
	def __str__(self):
		s = cStringIO.StringIO()
		for name in self:
			for header in self.get_list(name):
				s.write(normalize_header_name(name))
				s.write(': ')
				s.write(str(header))
				s.write('\n\r')
		
		s.seek(0)
		return s.read()
	
	def items(self):
		l = []
		for name in self:
			for header in self.get_list(name):
				l.append((normalize_header_name(name), str(header)))
		return l

class HTTPHeader(object):
	def __init__(self, name=None, value=None, **params):
		if name:
			self.name = normalize_header_name(name)
		else:
			name = None
		self.value = value
		self.params = params
	
	def __str__(self):
		s = cStringIO.StringIO()
		s.write(self.value)
		for k, v in sorted(self.params.iteritems()):
			s.write('; ')
			s.write(normalize_header_name(k, capwords=False))
			s.write('=')
			s.write(urln11n.quote(v))
		
		s.seek(0)
		return s.read()


class Fardel(ProtectedObject):
	def __init__(self, environ=None, request=None, response=None, 
	config=None, dirs=None, db=None, data=None, component_managers=None,
	component_agents=None, document=None):
		self._environ = environ
		self._request = request
		self._response = response	
		self._config = config
		self._dirs = dirs
		self._db = db
		self._data = data
		self._component_managers = component_managers
		self._component_agents = component_agents
		self._document = document
	
	def __getattr__(self, name):
		return getattr(self._component_agents, name)
	
	
	
	@property
	def env(self):
		return self._environ
	
	@property
	def req(self):
		return self._request
	
	@property
	def resp(self):
		return self._response
	
	@property
	def conf(self):
		return self._config
	
	@property
	def dirs(self):
		return self._dirs
	
	@property
	def data(self):
		return self._data
	
#	@property
#	def doc(self):
#		return self._document
#	
#	@doc.setter
#	def doc(self, d):
#		self._document = d
	
	@property
	def component_managers(self):
		return self._component_managers
		
	@property
	def component_agents(self):
		return self._component_agents
	
#	@property
#	def db(self):
#		return self._db
	
	def norm_url(self, url):
		if self._request.script_path:
			url.path = '%s/%s' % (self._request.script_path, url.path)

	def make_url(self, paths=None, params=None, query=None, fill=False):
		url = urln11n.URL()
		
		if fill:
			url.path = self._request.path
			url.params = self._request.params
			url.query = self._request.query
		
		if paths and (isinstance(paths, str) or isinstance(paths, unicode)):
			url.path = paths
		elif paths:
			url.path = '/'.join(paths)
		
		if params is not None:
			url.params = params
		
		if query is not None:
			url.query = query
		
		self.norm_url(url)
		return url
	
	def str_url(self, *args, **kargs):
		return str(self.make_url(*args, **kargs)) or '/'

class URL(urln11n.URL, BaseModel, ProtectedObject):
	class Renderer(BaseRenderer):
		@staticmethod
		def supports(format):
			return True
		
		@staticmethod
		def render(context, model, format='html'):
			return str(model)
	
	renderer = Renderer
	
	def __init__(self, *args, **kargs):
		urln11n.URL.__init__(self, *args, **kargs)
		BaseModel.__init__(self)
		ProtectedObject.__init__(self)


def normalize_header_name(name, capwords=True):
	if capwords:
		return string.capwords(name.replace('_', '-'), '-')
	else:
		return name.replace('_', '-')

