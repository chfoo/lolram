import lolram.web.framework.app
import tornado.web
import torwuf.web.controllers.base

class IndexController(lolram.web.framework.app.BaseController):
	def init(self):
		self.add_url_spec(r'/', IndexRequestHandler)
		self.add_url_spec(r'/(.*)', CatchAllRequestHandler)

class IndexRequestHandler(torwuf.web.controllers.base.BaseHandler):
	def get(self):
		self.render('index/index.html')

class CatchAllRequestHandler(torwuf.web.controllers.base.BaseHandler):
	def get(self, arg):
		raise tornado.web.HTTPError(500)