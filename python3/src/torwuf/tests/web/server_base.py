import lolram.tests.server_base
import tempfile
import torwuf.web.controllers.app

class ServerBaseMixIn(lolram.tests.server_base.ServerBaseMixIn):
	def create_app(self):
		self.temp_dir = tempfile.TemporaryDirectory()
		self.root_path = self.temp_dir.name
		self.app_wrapper = torwuf.web.controllers.app.Application(self.root_path)
		self.app = self.app_wrapper.wsgi_application