import lolram.web.framework.app

class IndexController(lolram.web.framework.app.BaseController):
	def init(self):
		self.add_url_spec(r'/(.*)', IndexRequestHandler)


class IndexRequestHandler(lolram.web.framework.app.BaseHandler):
	def get(self, arg):
		self.set_status(500)
		self.write('Sorry. Service not unavailable. Please try again later.'.encode())