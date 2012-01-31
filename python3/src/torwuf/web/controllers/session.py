import torwuf.web.controllers.base

class SessionController(torwuf.web.controllers.base.BaseController):
	def init(self):
		self.add_url_spec('/session/test', TestHandler)

class TestHandler(torwuf.web.controllers.base.BaseHandler):
	KEY = 'session_test_text'
	
	def get(self):
		self.render('session/test.html', text=self.session.get(TestHandler.KEY, ''))
	
	def post(self):
		self.session[TestHandler.KEY] = self.get_argument('text')
		self.session_commit()
		
		self.render('session/test.html', text=self.session.get(TestHandler.KEY))
