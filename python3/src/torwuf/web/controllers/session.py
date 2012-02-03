import torwuf.web.controllers.base

class SessionController(torwuf.web.controllers.base.BaseController):
	def init(self):
		self.add_url_spec('/session/test', TestHandler)
	
	# TODO: periodic maintenance (ie cleaning up old sessions)

class TestHandler(torwuf.web.controllers.base.BaseHandler):
	KEY = 'session_test_text'
	PERSISTENT_KEY = 'persistent_session_test_text'
	
	def get(self):
		self.render('session/test.html', 
			text=self.session.get(TestHandler.KEY, ''),
			persistent_text=self.persistent_session.get(TestHandler.PERSISTENT_KEY, ''),
		)
	
	def post(self):
		self.session[TestHandler.KEY] = self.get_argument('text', '')
		self.persistent_session[TestHandler.PERSISTENT_KEY] = self.get_argument('persistent_text', '')
		self.session_commit()
		
		self.render('session/test.html', 
			text=self.session.get(TestHandler.KEY, ''),
			persistent_text=self.persistent_session.get(TestHandler.PERSISTENT_KEY, ''),
		)
