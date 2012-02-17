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
import lolram.web.framework.app
import torwuf.web.controllers.error
import torwuf.web.controllers.sessionbase
from torwuf.web.controllers.authentication.mixins import AuthenticationHandlerMixIn

class BaseController(lolram.web.framework.app.BaseController):
	pass

class BaseHandler(lolram.web.framework.app.BaseHandler, 
torwuf.web.controllers.error.ErrorOutputHandlerMixin,
torwuf.web.controllers.sessionbase.SessionHandlerMixIn,
AuthenticationHandlerMixIn,
):
	def write_error(self, *args, **kargs):
		torwuf.web.controllers.error.\
			ErrorOutputHandlerMixin.write_error(self, *args, **kargs)
	
	def get_current_user(self):
		return AuthenticationHandlerMixIn.get_current_user(self)