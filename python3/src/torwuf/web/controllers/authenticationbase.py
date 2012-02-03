class AuthenticationHandlerMixIn(object):
	SESSION_OPENID_IDENTIY_URL = 'openid_id_url'
	SESSION_OPENID_DISPLAY_IDENTIFIER = 'openid_display_id'
	
	def get_current_user(self):
		return self.session_get_any(
			AuthenticationHandlerMixIn.SESSION_OPENID_IDENTIY_URL)
	
	def get_openid_identity_url(self):
		return self.session_get_any(
			AuthenticationHandlerMixIn.SESSION_OPENID_IDENTIY_URL)
	
	def get_openid_display_id(self):
		return self.session_get_any(
			AuthenticationHandlerMixIn.SESSION_OPENID_DISPLAY_IDENTIFIER)
	
	def clear_current_user(self):
		key1 = AuthenticationHandlerMixIn.SESSION_OPENID_IDENTIY_URL
		key2 = AuthenticationHandlerMixIn.SESSION_OPENID_DISPLAY_IDENTIFIER
		
		self.session.pop(key1, None)
		self.session.pop(key2, None)
		self.persistent_session.pop(key1, None)
		self.persistent_session.pop(key2, None)