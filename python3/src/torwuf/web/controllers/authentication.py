import torwuf.web.controllers.base
import openid.consumer

class AuthenticationController(torwuf.web.controllers.base.BaseController):
	def init(self):
		self.add_url_spec('/authentication/show_openid', ShowOpenIDHandler)


class ShowOpenIDHandler(torwuf.web.controllers.base.BaseHandler):
	pass
