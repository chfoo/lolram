import lolram.web.framework.app
import torwuf.web.controllers.index

class Application(lolram.web.framework.app.ApplicationController):
	controller_classes = [torwuf.web.controllers.index.IndexController,]
	
	def __init__(self, root_path):
		lolram.web.framework.app.ApplicationController.__init__(self, 
			root_path, Application.controller_classes)
	
	def init_database(self):
		pass #TODO
