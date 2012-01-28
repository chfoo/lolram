import logging
import lolram.web.framework.app
import os.path
import pymongo.connection
import torwuf.web.controllers.bzr
import torwuf.web.controllers.index
import torwuf.web.controllers.resource
import torwuf.web.controllers.security
import torwuf.web.controllers.xkcd_geocities
import torwuf.web.views

_logger = logging.getLogger(__name__)

class Application(lolram.web.framework.app.ApplicationController):
	controller_classes = [
		torwuf.web.controllers.security.LoginRateLimitController,
		torwuf.web.controllers.bzr.BzrController,
		torwuf.web.controllers.resource.ResourceController,
		torwuf.web.controllers.xkcd_geocities.XKCDGeocitiesController,
		
		torwuf.web.controllers.index.IndexController,
	]
	
	def __init__(self, configuration):
		_logger.info('APP INIT')
		
		template_path = self._get_template_path()
		configuration.tornado_settings.update({
			'xsrf_cookies': True,
			'cookie_secret': configuration\
				.config_parser['application']['cookie-secret'],
			'template_path': template_path,
		})
		
		lolram.web.framework.app.ApplicationController.__init__(self,
			configuration, Application.controller_classes)
		
		_logger.debug('Debug=%s', self.config.debug_mode)
	
	def _get_template_path(self):
		return os.path.join(os.path.dirname(torwuf.web.views.__file__),
			'templates')
	
	def init_database(self):
		db_name = self.config.config_parser['mongodb']['database']
		username = self.config.config_parser['mongodb']['username']
		password = self.config.config_parser['mongodb']['password']
		self._db_connection = pymongo.connection.Connection('127.0.0.1')
		self._database = self._db_connection[db_name]
		auth_result = self._database.authenticate(username, password)
		
		# To propagate our authentication to the sockets immediately,
		# we must terminate and it will reconnect 
		# FIXME: this solution does not work, workaround is to disable auth
		self._db_connection.disconnect()
		
		_logger.info('MongoDB Login result=%s', auth_result)
	
	def init_cache(self):
		# TODO: use memcached
		pass
	
	@property
	def resource_path(self):
		return os.path.join(os.path.dirname(torwuf.web.views.__file__),
			'resources')
