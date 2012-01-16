import lolram.web.framework.app
import os.path
import torwuf.web.controllers.index
import torwuf.web.controllers.bzr
import torwuf.web.views

class Application(lolram.web.framework.app.ApplicationController):
	controller_classes = [
		torwuf.web.controllers.index.IndexController,
		torwuf.web.controllers.bzr.BzrController,
	]
	
	def __init__(self, configuration):
		template_path = self._get_template_path()
		configuration.tornado_settings.update({
			'xsrf_cookies': True,
			'cookie_secret': configuration\
				.config_parser['application']['cookie-secret'],
			'template_path': template_path,
		})
		
		lolram.web.framework.app.ApplicationController.__init__(self,
			configuration, Application.controller_classes)
	
	def _get_template_path(self):
		return os.path.join(os.path.dirname(torwuf.web.views.__file__),
			'templates')
	
	def init_database(self):
		pass #TODO
