import configparser
import logging
import lolram.web.tornado
import os.path
import tempfile
import tornado.web

_logger = logging.getLogger(__name__)

class Configuration(object):
	def __init__(self, root_path, debug_mode=False):
		self._root_path = root_path
		self._debug_mode = debug_mode
		
		self.read_config_file()
		self.create_db_dirs()
	
	@property
	def root_path(self):
		return self._root_path
	
	@property
	def debug_mode(self):
		return self._debug_mode
	
	@property
	def db_path(self):
		return self._db_path
	
	@property
	def upload_path(self):
		return self._upload_path
	
	def read_config_file(self):
		if self._debug_mode:
			config_filename = 'app_debug.config'
		else:
			config_filename = 'app.config'
		
		config_parser = configparser.ConfigParser()
		config_path = os.path.join(self._root_path, config_filename)
		
		_logger.info('Configuration file path: %s', config_path)
		
		sucessful_files = config_parser.read([config_path])
		
		if sucessful_files:
			_logger.debug('Read %s configuration files', len(sucessful_files))
		else:
			_logger.warn('No configuration files read')
	
	def create_db_dirs(self):
		if self.debug_mode:
			self._temp_dir = tempfile.TemporaryDirectory()
			self._db_path = self._temp_dir.name
			_logger.info('Using temporary directory')
		else:
			self._db_path = os.path.join(self.root_path, 'databases/')
		
		self._upload_path = os.path.join(self._db_path, 'uploads/')
		
		_logger.info('Database path: %s', self._db_path)
		
		if not os.path.exists(self._db_path):
			_logger.info('Creating path %s', self._db_path)
			os.makedirs(self._db_path)
		
		if not os.path.exists(self._upload_path):
			_logger.info('Creating path %s', self._upload_path)
			os.makedirs(self._upload_path)

	
class ApplicationController(object):
	def __init__(self, root_path, controller_classes, debug_mode=False):
		self._root_path = root_path
		self._configuration = Configuration(root_path, debug_mode)
		
		self.init_database()
		self.init_url_specs(controller_classes)
		self.init_wsgi_application()
		
	@property
	def configuration(self):
		return self._configuration
	
	@property
	def wsgi_application(self):
		return self._wsgi_application
	
	@property
	def database(self):
		return self._database
	
	def init_url_specs(self, controller_classes):
		self._url_specs = []
		
		for controller_class in controller_classes:
			controller = controller_class(self)
			self._url_specs.extend(controller.url_specs)
		
	def init_wsgi_application(self):
		self._wsgi_application = lolram.web.tornado.WSGIApplication()
	
	def init_database(self):
		raise NotImplementedError()


class BaseController(object):
	def __init__(self, application):
		self._application = application
		self._url_specs = []
		self.init()
		
	def init(self):
		pass
	
	@property
	def application(self):
		self._application
	
	@property
	def url_specs(self):
		return self._url_specs
	
	def add_url_spec(self, url_pattern, handler_class):
		url_spec = tornado.web.URLSpec(url_pattern, handler_class, 
			controller=self, name=handler_class.name)
		self._url_specs.append(url_spec)


class BaseHandler(tornado.web.RequestHandler):
	name = NotImplemented
	
	@property
	def controller(self):
		self._controller
		
	@property
	def application(self):
		self._controller.application
	
	def initialize(self, controller):
		self._controller
		self.init()
	
	def init(self):
		pass


