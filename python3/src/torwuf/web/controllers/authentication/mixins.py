from torwuf.web.models.authentication import SessionKeys


class AuthenticationHandlerMixIn(object):
	def get_current_user(self):
		return self.session_get_any(SessionKeys.CURRENT_HEX_ID)


class ProcessingMixIn(object):
	# XXX: It is important that realm must stay static as much as possible
	# Otherwise Google will return useless identity urls
	def get_openid_realm(self):
		if self.request.host.split(':', 1)[0] in ('localhost', '127.0.0.1'):
			return self.request.protocol + '://' + self.request.host
		else:
			return self.request.protocol + '://*.' + self.request.host

