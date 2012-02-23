'''Things that controllers and handlers should inherit'''
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
from torwuf.web.controllers.account.authentication.mixins import \
	AuthenticationHandlerMixIn
from torwuf.web.controllers.session.mixin import SessionHandlerMixIn
import logging
import lolram.web.framework.app
import torwuf.web.controllers.error

_logger = logging.getLogger(__name__)

class BaseController(lolram.web.framework.app.BaseController):
	pass

class BaseHandler(lolram.web.framework.app.BaseHandler, 
torwuf.web.controllers.error.ErrorOutputHandlerMixin,
SessionHandlerMixIn,
AuthenticationHandlerMixIn,
):
	MESSAGE_SESSION_KEY = '_messages'
	
	def write_error(self, *args, **kargs):
		torwuf.web.controllers.error.\
			ErrorOutputHandlerMixin.write_error(self, *args, **kargs)
	
	def get_current_user(self):
		return AuthenticationHandlerMixIn.get_current_user(self)
	
	def render(self, template_name, **kargs):
		if BaseHandler.MESSAGE_SESSION_KEY in self.session:
			if not hasattr(self.request, 'messages'):
				self.request.messages = []
			
			self.request.messages.extend(self.session[BaseHandler.MESSAGE_SESSION_KEY])
		
		lolram.web.framework.app.BaseHandler.render(self, template_name, **kargs)
	
	def add_message(self, title, body=None):
		if not hasattr(self.request, 'messages'):
			self.request.messages = []
		
		self.request.messages.append((title, body))
	
	def finish(self, chunk=None):
		if hasattr(self.request, 'messages') and self.request.messages:
			with self.get_session() as session:
				session[BaseHandler.MESSAGE_SESSION_KEY] = self.request.messages
		elif hasattr(self.request, 'messages'):
			with self.get_session() as session:
				session.pop(BaseHandler.MESSAGE_SESSION_KEY, None)
		
		lolram.web.framework.app.BaseHandler.finish(self, chunk)
