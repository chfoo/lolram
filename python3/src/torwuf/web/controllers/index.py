import lolram.web.framework.app

class IndexController(lolram.web.framework.app.BaseController):
	def init(self):
		self.add_url_spec('/*', IndexRequestHandler)


class IndexRequestHandler(lolram.web.framework.app.BaseHandler):
	def get(self):
		self.write(b'sandwiches')