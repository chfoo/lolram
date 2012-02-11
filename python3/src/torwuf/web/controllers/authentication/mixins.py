from torwuf.web.models.authentication import SessionKeys
import base64
import functools
import uuid


class AuthenticationHandlerMixIn(object):
	def get_current_user(self):
		current_account_id = self.session_get_any(SessionKeys.CURRENT_ACCOUNT_ID)
		
		if current_account_id:
			return 'account:%s' % current_account_id
		
		openid_id = self.session_get_any(SessionKeys.CURRENT_OPENID)
		
		if openid_id:
			return 'openid:%s' % openid_id
	
	@property
	def current_account_id(self):
		return self.session_get_any(SessionKeys.CURRENT_ACCOUNT_ID)
	
	@current_account_id.setter
	def current_account_id(self, str_or_byte_id):
		if isinstance(str_or_byte_id, str):
			self.session[SessionKeys.CURRENT_ACCOUNT_ID] = str_or_byte_id.lower()
		else:
			self.session[SessionKeys.CURRENT_ACCOUNT_ID] = str(
				base64.b16encode(str_or_byte_id), 'utf8').lower()
	
	@property
	def current_account_uuid(self):
		hex_str = self.current_account_id
		
		if hex_str:
			return uuid.UUID(hex_str)
	
	@property
	def current_openid(self):
		return self.session_get_any(SessionKeys.CURRENT_OPENID)
	
	def logout(self):
		self.session.pop(SessionKeys.CURRENT_ACCOUNT_ID, None)
		self.session.pop(SessionKeys.CURRENT_OPENID, None)
		self.persistent_session.pop(SessionKeys.CURRENT_ACCOUNT_ID, None)
		self.persistent_session.pop(SessionKeys.CURRENT_OPENID, None)
	
	@staticmethod
	def require_account(fn):
		def wrapper(self, *args, **kargs):
			if not self.current_account_id:
				self.redirect('/account/login')
			else:
				return fn(self, *args, **kargs)
			
		return wrapper

class ProcessingMixIn(object):
	# XXX: It is important that realm must stay static as much as possible
	# Otherwise Google will return useless identity urls
	def get_openid_realm(self):
		if self.request.host.split(':', 1)[0] in ('localhost', '127.0.0.1'):
			return self.request.protocol + '://' + self.request.host
		else:
			return self.request.protocol + '://*.' + self.request.host

