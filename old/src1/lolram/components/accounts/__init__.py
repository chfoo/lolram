# encoding=utf8

'''User account and profiles'''

#	Copyright © 2011 Christopher Foo <chris.foo@gmail.com>

#	This file is part of Lolram.

#	Lolram is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.

#	Lolram is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.

#	You should have received a copy of the GNU General Public License
#	along with Lolram.  If not, see <http://www.gnu.org/licenses/>.

__docformat__ = 'restructuredtext en'

import os
import hashlib
import datetime
import time
import json
import cPickle as pickle
import collections

import sqlalchemy
from sqlalchemy import *
from sqlalchemy.orm import relationship, synonym

import openid.store.interface
import openid.consumer.consumer
import openid.association
import openid.store.nonce

from lxml.html import builder as lxmlbuilder

from lolram import configloader, models, dataobject, views, util
from lolram.components import base, session, wui
from lolram.components.accounts.dbdefs import *
from lolram.widgets import TextBox
from lolram.components.database import Database


class AccountRole(collections.namedtuple('AccountRole', 
['namespace', 'code', 'label', 'default'])):
	'''Account role
	
	If ``default`` is `True`, new accounts will have this role
	applied to the account.
	'''

	def __new__(self, namespace, code, label=None, default=False):
		return super(AccountRole, self).__new__(self, namespace, code, label, default)


class AccountManager(base.BaseComponent):
	'''Manages and audits accounts
	
	A simple password authentication is supported. See the `default_config`
	variable and configure the hash and salt values to enable this feature.
	'''
	
	default_config = configloader.DefaultSectionConfig('accounts',
		master_test_password_salt=0,
		master_test_password_sha256_hex=0,
		master_test_username='root',
	)
	
	class Roles(object):
		NAMESPACE = 'lracc'
		ADMIN = AccountRole(NAMESPACE, 1, 'Admin')
		BOT = AccountRole(NAMESPACE, 2, 'Bot')
		GUEST = AccountRole(NAMESPACE, 3, 'Guest', default=True)
		USER = AccountRole(NAMESPACE, 4, 'User')
		SUPERUSER = AccountRole(NAMESPACE, 5, 'Superuser')
		OPERATOR = AccountRole(NAMESPACE, 6, 'Operator')
		CAPTCHA_SOLVED = AccountRole(NAMESPACE, 7, 'Captcha Solved')
	
	def init(self):
		db = self.context.get_instance(database.Database)
		db.add(AccountsMeta, AccountLogsMeta, OpenIDAssocMeta, OpenIDNonceMeta,
			AccountCaptchaMeta)
		self._roles = set()
		
		if self.context.config.accounts.master_test_username \
		and self.context.config.accounts.master_test_password_sha256_hex:
			self._has_test_account_setup = False
		else:
			self._has_test_account_setup = True
		
		self.register_roles(self.Roles.ADMIN,
			self.Roles.BOT,
			self.Roles.GUEST,
			self.Roles.USER,
			self.Roles.SUPERUSER,
			self.Roles.OPERATOR,
			self.Roles.CAPTCHA_SOLVED)
	
	def run_maintenance(self):
		openid_store = OpenIDDBStore(self.context)
		openid_store.cleanup()
		
		db = self.context.get_instance(database.Database)
		AccountCaptcha = db.models.AccountCaptcha
		query = db.session.query(AccountCaptcha) \
			.filter(sqlalchemy.or_(AccountCaptcha.valid==False, AccountCaptcha.created < time.time() - 3600))
		query.delete()
		
	def setup(self):
		if not self.singleton._has_test_account_setup:
			db = self.context.get_instance(database.Database)
			username = self.context.config.accounts.master_test_username
			query = db.session.query(db.models.Account).filter_by(
				username=username)
		
			if not query.first() and username:
				model = db.models.Account(username=username)
				db.session.add(model)
				db.session.flush()
			
			self.singleton._has_test_account_setup = True
		
		sess = self.context.get_instance(session.Session)
		self._account_id = sess.data._accounts_account_id
	
	def register_roles(self, *account_roles):
		'''Register roles accounts may have
		
		:parameters:
			account_roles : `AccountRole`
				The `AccountRole`
		'''
		
		for role in account_roles:
			self.master._roles.add(role)
	
	def is_authenticated(self):
		'''Checks if user is authenticated
		
		:rtype: `bool`
		:return: `True` if authenticated
		'''
		
		return self._account_id is not None
	
	def is_authorized(self, account_role):
		'''Checks if user is authorized
		
		:parameters:
			account_role : `AccountRole`
				The account role to check
		
		:rtype: `bool`
		:return: `True` if authorized
		'''
		
		if not self.is_authenticated:
			return False
		
		model = self.get_account_model(self.account_id)
		
		if not model:
			return False
		
		if model.username == self.context.config.accounts.master_test_username \
		and self.context.config.accounts.master_test_password_sha256_hex:
			return True
			
		
		return (account_role.namespace, account_role.code) in model.roles
	
	@property
	def account_id(self):
		'''Return ID of account in database
		
		:rtype: `int`
		'''
		
		return self._account_id
	
	@property
	def account_model(self):
		'''Return database model
		
		:rtype: `lolram.components.accounts.dbdef.Account`
		'''
		
		if self.account_id:
			db = database.Database(self.context)
			query = db.session.query(db.models.Account).filter_by(
				id=self.account_id)
			return query.first()
		
	def get_account_model(self, account_id):
		'''Return database model
		
		:rtype: `lolram.components.accounts.dbdef.Account`
		'''
		
		db = database.Database(self.context)
		query = db.session.query(db.models.Account).filter_by(id=account_id)
		
		return query.first()
	
	def authenticate_openid_stage_1(self, openid_url, return_to_url):
		'''Stage 1 of the OpenID authentication
		
		:rtype: `str`
		:return: The URL the client must go to
		'''
		
		sess = session.Session(self.context)
		realm = return_to_url
		s = dict() 
		store = OpenIDDBStore(self.context)
		consumer = openid.consumer.consumer.Consumer(s, store)
		auth_request = consumer.begin(openid_url)
		redirect_url = auth_request.redirectURL(realm, return_to_url)
		sess.data._openid_pickle = pickle.dumps(s)
		
		self.context.logger.debug(u'Return to url: %s' % return_to_url)
		
		return redirect_url
	
	def authenticate_openid_stage_2(self):
		'''Stage 2 of the OpenID authentication
		
		:rtype: `tuple`
		:return: A `tuple` containing:
			
			1. Account name
			2. Account unique ID
			3. Result code
		'''
		
		sess = self.context.get_instance(session.Session)
		s = pickle.loads(str(sess.data._openid_pickle))
		store = OpenIDDBStore(self.context)
		consumer = openid.consumer.consumer.Consumer(s, store)
		request_url = str(self.context.request.url)
		query_args = self.context.request.url.get_query_first()
		result_code = consumer.complete(query_args, request_url)
		
		self.context.logger.debug(u'Stage 2 request_url %s query %s result code %s' % (request_url, query_args, result_code))
		
		del sess.data._openid_pickle
		
		if isinstance(result_code, openid.consumer.consumer.CancelResponse):
			return (None, None, result_code)
		elif isinstance(result_code, openid.consumer.consumer.FailureResponse):
			return (None, None, result_code)
		elif isinstance(result_code, openid.consumer.consumer.SetupNeededResponse):
			raise Exception('Recieved code despite not in intermediate mode')
		elif isinstance(result_code, openid.consumer.consumer.SuccessResponse):
			return (result_code.getDisplayIdentifier(), 
				result_code.identity_url, result_code)
		else:
			raise Exception('Unexpected code')
	
	def authenticate_testing_password(self, password):
		'''Simple password authentication
		
		:rtype: `bool`
		'''
		
		db = database.Database(self.context)
		
		if isinstance(password, unicode):
			password = password.encode('utf8')
		
		sha256_obj = hashlib.sha256(password)
		
		salt = self.context.config.accounts.master_test_password_salt
		
		if not salt:
			raise Exception('Salt not defined')
		
		sha256_obj.update(salt)
		
		hex1 = sha256_obj.hexdigest().lower()
		hex2 = self.context.config.accounts.master_test_password_sha256_hex
		
		username = self.context.config.accounts.master_test_username
		query = db.session.query(db.models.Account).filter_by(
			username=username)
		model = query.first()
		
		if hex2 and hex1 == hex2.lower() and model:
			self.apply_account_id(model.id)
		
		return self._account_id
	
	def apply_account_id(self, account_id):
		'''Associate the account to this session'''
		
		event = {'prev_acc': self.account_id}
		
		self.context.logger.debug(u'Apply account id %s', account_id)
		self._account_id = account_id
		sess = session.Session(self.context)
		sess.data._accounts_account_id = account_id
		
		model = self.get_account_model(account_id)
		
		if not model.sessions:
			model.sessions = self._session_data_template()
		
		
		self.log_event(AccountLogsMeta.NS_ACCOUNTS, 
			AccountLogsMeta.CODE_SESSION_ACTIVATE, info=event)
	
	def _session_data_template(self):
		d = {'date': time.time()}
		return d
	
	def log_event(self, namespace, code, info=None, include_ip=True):
		if info is None:
			info = {}
		
		if include_ip:
			info['ip'] = self.context.environ.get('REMOTE_ADDR')
		
		if not info:
			info = None
		
		db = database.Database(self.context)
		log_model = db.models.AccountLog()
		log_model.account_id = self.account_id
		log_model.namespace = namespace
		log_model.action_code = code
		log_model.info = info
		db.session.add(log_model)
	
	def cancel_account_id(self):
		'''Remove association of the account from this session'''
		
		self.context.logger.debug(u'Cancel account id %s', self._account_id)
		
		event = {'prev_acc': self.account_id}
		
		self.log_event(AccountLogsMeta.NS_ACCOUNTS, 
			AccountLogsMeta.CODE_SESSION_DEACTIVATE, info=event)
		
		self._account_id = None
		sess = session.Session(self.context)
		
		# suppress warning unused sess variable
		sess
		
		del sess.data._accounts_account_id
	
	@property
	def roles(self):
		return self.master._roles

class CaptchaValidator(dataobject.ContextAware):
	CAPTCHA_KEY = 'lraccc'
	CAPTCHA_KEY_ANS = CAPTCHA_KEY + 'ans'
	
	def new(self):
		db = Database(self.context)
		
		captcha = db.models.AccountCaptcha()
		captcha.question, captcha.answer = util.make_math1()
		
		db.session.add(captcha)
		db.session.flush()
		
		return captcha
	
	def validate(self, id_, key, answer):
		db = database.Database(self.context)
		query = db.session.query(db.models.AccountCaptcha) \
			.filter_by(id=id_).filter_by(key=key).filter_by(valid=True)
		
		captcha = query.first()
		
		if captcha:
			captcha.valid = False
		
		if captcha and util.str_to_int(answer) == int(captcha.answer):
			return True
		
		return False
	
	def form_validate(self):
		val = self.context.request.form.getfirst(self.CAPTCHA_KEY)
		ans = self.context.request.form.getfirst(self.CAPTCHA_KEY_ANS)
		
		id_, key = val.split('.')
		key = util.b32low_to_bytes(key)
		
		return self.validate(id_, key, ans)
	
	def add_form(self, form):
		captcha = self.new()
		val = '%s.%s' % (captcha.id, util.bytes_to_b32low(captcha.key))
		
		form[self.CAPTCHA_KEY] = TextBox(value=val, validation=TextBox.HIDDEN)
		form[self.CAPTCHA_KEY_ANS] = TextBox(label=captcha.question, required=True)
		
		return form

	
__all__ = ('AccountManager', 'AccountRole', 'CaptchaValidator')
