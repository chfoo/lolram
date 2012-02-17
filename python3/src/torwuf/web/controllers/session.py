'''Sessions using cookies controller'''
#
#	Copyright (c) 2012 Christopher Foo <chris.foo@gmail.com>
#
#	This file is part of Torwuf.
#
#	Torwuf is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	Torwuf is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with Torwuf.  If not, see <http://www.gnu.org/licenses/>.
#
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
