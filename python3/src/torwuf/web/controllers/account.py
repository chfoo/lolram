from torwuf.web.models.account import AccountCollection
import string
import tornado.web
import torwuf.web.controllers.base
import bson.objectid

VALID_USERNAME_SET = frozenset(string.ascii_lowercase) \
	| frozenset(string.digits)

def validate_username_chars(username):
	return frozenset(username) <= VALID_USERNAME_SET

def normalize_username(username):
	username = username.lower().strip('._-')
	
	if validate_username_chars(username):
		return username

class AccountController(torwuf.web.controllers.base.BaseController):
	def init(self):
		self.add_url_spec('/account/openid_sucesss', OpenIDSuccessHandler)
		self.add_url_spec('/account/profile', ProfileHandler)
#		self.add_url_spec('/account/profile/edit', EditProfileHandler)
#		self.add_url_spec('/account/passwords', PasswordsHandler)
#		self.add_url_spec('/account/passwords/add', AddPasswordHandler)
#		self.add_url_spec('/account/passwords/delete', DeletePasswordHandler)


class HandlerMixIn(object):
	@property
	def account_collection(self):
		return self.app_controller.database[AccountCollection.COLLECTION]
	
	@property
	def current_user_id(self):
		return bson.objectid.ObjectId(self.current_user)


class ProfileHandler(torwuf.web.controllers.base.BaseHandler, HandlerMixIn):
	@tornado.web.authenticated
	def get(self):
		result = self.account_collection.find_one({'id_': self.current_user_id})
		
		self.render('account/profile.html', model_keys=AccountCollection,
			model_data=result)


class OpenIDSuccessHandler(object):
	def get(self):
		pass