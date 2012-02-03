import lolram.web.framework.app
import torwuf.web.controllers.error
import torwuf.web.controllers.sessionbase
import torwuf.web.controllers.authenticationbase

class BaseController(lolram.web.framework.app.BaseController):
	pass

class BaseHandler(lolram.web.framework.app.BaseHandler, 
torwuf.web.controllers.error.ErrorOutputHandlerMixin,
torwuf.web.controllers.sessionbase.SessionHandlerMixIn,
torwuf.web.controllers.authenticationbase.AuthenticationHandlerMixIn,
):
	def write_error(self, *args, **kargs):
		torwuf.web.controllers.error.\
			ErrorOutputHandlerMixin.write_error(self, *args, **kargs)
	
	def get_current_user(self):
		return torwuf.web.controllers.authenticationbase.\
			AuthenticationHandlerMixIn.get_current_user(self)