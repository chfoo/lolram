from .authenticationbase import AuthenticationHandlerMixIn
import torwuf.web.controllers.base
import urllib.parse
import xmlrpc.client

class AuthenticationController(torwuf.web.controllers.base.BaseController):
	def init(self):
		self.add_url_spec('/authentication/show_openid', ShowOpenIDHandler)
		self.add_url_spec('/authentication/openid_stage_1', OpenIDStage1Handler)
		self.add_url_spec('/authentication/openid_stage_2', OpenIDStage2Handler)
		self.add_url_spec('/authentication/login', LoginHandler)
		self.add_url_spec('/authentication/logout', LogoutHandler)
		
		self.init_server_proxy()
	
	def init_server_proxy(self):
		address = 'http://%s:%s/' % (
			self.config.config_parser['rpc2to3']['address'],
			self.config.config_parser.getint('rpc2to3', 'port')
		)
		
		self.rpc_server =  xmlrpc.client.ServerProxy(address)


class ShowOpenIDHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'authen_show_openid'
	
	def get(self):
		self.render('authentication/show_openid.html',
			display_id=self.get_openid_display_id(),
			identity_url=self.get_openid_identity_url(),
		)

class OpenIDBaseHandler(torwuf.web.controllers.base.BaseHandler):
	SESSION_KEY = 'openid_session'
	SESSION_RECENT_FAILURE_KEY = 'openid_failure'
	HTTPS_WILDCARD_REALM = 'https://*.torwuf.com'
	
	def get_realm(self):
		if self.request.host.split(':', 1)[0] in ('localhost', '127.0.0.1'):
			return self.request.protocol + '://' + self.request.host
		else:
			return OpenIDBaseHandler.HTTPS_WILDCARD_REALM
	
	def set_openid_failure_flag(self):
		self.session[OpenIDBaseHandler.SESSION_RECENT_FAILURE_KEY] = True
	
	def get_openid_failure_flag(self):
		return self.session.get(OpenIDBaseHandler.SESSION_RECENT_FAILURE_KEY)
	
	def clear_openid_failure_flag(self):
		self.session.pop(OpenIDBaseHandler.SESSION_RECENT_FAILURE_KEY, None)
	

class LoginHandler(OpenIDBaseHandler):
	name = 'authen_login'
	
	def get(self):
		if self.get_current_user():
			self.redirect('/account/')
		
		render_dict = {
			'realm': self.get_realm()
		}
		
		if self.get_openid_failure_flag():
			render_dict['layout_message_title'] = self.locale.translate('There was a problem signing in')
			render_dict['layout_message_body'] = self.locale.translate('Please check for mistakes and try again.')
			
			self.clear_openid_failure_flag()
			self.session_commit()
		
		self.render('authentication/login.html',
			**render_dict
		)

class OpenIDStage1Handler(OpenIDBaseHandler):
	name = 'authen_openid_stage_1'
	
	def post(self):
		realm = self.get_realm()
		openid_url = self.get_argument('openid_url')
		destination = self.get_argument('destination', '')
		persistent = self.get_argument('persistent', '')
		return_to_url = self.request.protocol + "://" + self.request.host + \
			self.reverse_url(OpenIDStage2Handler.name)
		return_to_url += '?destination=%s&persistent=%s' % (destination,
			persistent)
		result = self.controller.rpc_server.openid_stage_1(openid_url, 
			return_to_url, realm)
		
		if result:
			redirect_url, session_data = result
			self.session[OpenIDBaseHandler.SESSION_KEY] = session_data
			self.session_commit()
			self.redirect(redirect_url)
		else:
			self.set_openid_failure_flag()
			self.session_commit()
			self.redirect(return_to_url)


class OpenIDStage2Handler(OpenIDBaseHandler):
	name = 'authen_openid_stage_2'
	destination_table = {
		'show_openid': ShowOpenIDHandler.name
	}
	
	def get(self):
		query_kvp_dict = dict(urllib.parse.parse_qsl(self.request.query))
		session_data = self.session.get(OpenIDBaseHandler.SESSION_KEY, '')
		be_persistent = self.get_argument('persistent', False)
		
		result = self.controller.rpc_server.openid_stage_2(session_data, 
			query_kvp_dict, self.request.full_url())
		
		if result:
			identity_url, display_id = result
			session = self._persistent_session if be_persistent else self.session
			session[AuthenticationHandlerMixIn.\
				SESSION_OPENID_IDENTIY_URL] = identity_url
			session[AuthenticationHandlerMixIn.\
				SESSION_OPENID_DISPLAY_IDENTIFIER] = display_id
				
			self.session.pop(OpenIDBaseHandler.SESSION_KEY, None)
		else:
			self.set_openid_failure_flag()
		
		self.session_commit()
		self.forward_user_to_destination()
	
	def forward_user_to_destination(self):
		name = OpenIDStage2Handler.destination_table.get(
			self.get_argument('destination', None))
		
		if name:
			self.redirect(self.reverse_url(name), permanent=False)
		else:
			self.redirect(self.reverse_url(LoginHandler.name), permanent=False)

class LogoutHandler(OpenIDBaseHandler):
	name = 'authen_logout'
	
	def get(self):
		self.clear_current_user()
		self.session_commit()
		self.render('authentication/logout.html')
