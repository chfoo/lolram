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
import random
import cPickle as pickle

from sqlalchemy import *
from sqlalchemy.orm import relationship, synonym

import openid.store.interface
import openid.consumer.consumer
import openid.association
import openid.store.nonce

from lxml.html import builder as lxmlbuilder

import base
from .. import dataobject
from .. import configloader
from .. import models
from .. import views
import database
import session
import wui

class AccountsMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class Account(database.TableMeta.Def.base()):
			__tablename__ = 'accounts'
			
			id = Column(Integer, primary_key=True)
			username = Column(Unicode(length=255), nullable=False, unique=True, 
				index=True)
			password = Column(LargeBinary(length=16))
			created = Column(DateTime, default=datetime.datetime.utcnow)
			modified = Column(DateTime, default=datetime.datetime.utcnow,
				onupdate=datetime.datetime.utcnow)
			nickname = Column(Unicode(length=160))
			_roles = Column('roles', Unicode(length=255))
			_sessions = Column('sessions', Unicode(length=255))
			_profile_data = Column('profile_data', UnicodeText)
			
			@property
			def roles(self):
				return frozenset(map(tuple, json.loads(self._roles or '[]')))
			
			@roles.setter
			def roles(self, iterable):
				self._roles = json.dumps(tuple(iterable))
			
			def add_role(self, namespace, code):
				self.roles = self.roles | frozenset((namespace, code))
			
			def remove_role(self, namespace, code):
				self.roles = self.roles - frozenset((namespace, code))
			
			roles = synonym('_roles', descriptor=roles)
			
			@property
			def sessions(self):
				return json.loads(self._sessions or 'null')
			
			@sessions.setter
			def sessions(self, v):
				self._sessions = json.dumps(v)
				
			sessions = synonym('_sessions', descriptor=sessions)
			
			@property
			def profile_data(self):
				return json.loads(self._profile_data or 'null')
			
			@profile_data.setter
			def profile_data(self, v):
				self._profile_data = json.dumps(v)
			
			profile_data = synonym('_profile_data', descriptor=profile_data)
			
		desc = 'new table'
		model = Account
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine) 
	
	uuid = 'urn:uuid:6f82230b-4f38-4e9f-b32c-6a877e8361bd'
	defs = (D1,)


class AccountLogsMeta(database.TableMeta):
	NS_ACCOUNTS = 'lr-accs'
	CODE_SESSION_ACTIVATE = 1
	CODE_SESSION_DEACTIVATE = 2
	CODE_ROLE_MODIFY = 3
	
	class D1(database.TableMeta.Def):
		class AccountLog(database.TableMeta.Def.base()):
			__tablename__ = 'account_logs'
			
			id = Column(Integer, primary_key=True)
			account_id = Column(ForeignKey(AccountsMeta.D1.Account.id), 
				nullable=False, index=True)
			account = relationship(AccountsMeta.D1.Account)
			namespace = Column(Unicode(length=8), nullable=False)
			action_code = Column(Integer, nullable=False)
			created = Column(DateTime, default=datetime.datetime.utcnow)
			_info = Column('info', Unicode(length=255))
			
			@property
			def info(self):
				return json.loads(self._info or 'null')
			
			@info.setter
			def info(self, v):
				self._info = json.dumps(v)
			
			info = synonym('_info', descriptor=info)
			
		desc = 'new table'
		model = AccountLog
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine) 
			
	uuid = 'urn:uuid:0668d150-bd8a-4067-94c8-7ae8edcaddb3'
	defs = (D1,)

class OpenIDNonceMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class OpenIDNonce(database.TableMeta.Def.base()):
			__tablename__ = 'openid_nonces'
			server_url = Column(String, primary_key=True)
			timestamp = Column(Integer, primary_key=True)
			salt = Column(String(length=40), primary_key=True)
		
		desc = 'new table'
		model = OpenIDNonce
	
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine) 
			
	uuid = 'urn:uuid:62f935a3-b4e7-476b-b774-369468a88673'
	defs = (D1,)

class OpenIDAssocMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class OpenIDAssoc(database.TableMeta.Def.base()):
			__tablename__ = 'openid_assocs'
			server_url = Column(String, primary_key=True)
			handle = Column(String, primary_key=True)
			secret = Column(LargeBinary(length=128))
			issued = Column(Integer)
			lifetime = Column(Integer)
			assoc_type = Column(String(length=64))
		
		desc = 'new table'
		model = OpenIDAssoc
	
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine) 
			
	uuid = 'urn:uuid:1554b8da-f8f3-4703-8691-9eb21e6f94c3'
	defs = (D1,)


class OpenIDInfo(object):
	providers = {
		'google' : ('google.com/accounts/o8/id', 'Google'),
		'yahoo' : ('me.yahoo.com', 'Yahoo!'),
		'microsoft' : ('accountservices.passport.net', 'Windows Live'),
		'livejournal' : ('{{}}.livejournal.com', 'LiveJournal', ),
		'myspace' : ('myspace.com/{{}}', 'MySpace'),
		'wordpress' : ('{{}}.wordpress.com', 'WordPress'),
		'blogger' : ('{{}}.blogger.com', 'Blogger',),
		'verisign' : ('{{}}.pip.verisignlabs.com', 'Verisign'),
		'launchpad' : ('launchpad.net/~{{}}', 'Launchpad'),
		'facebook' : ('facebook.com/{{}}', 'Facebook'),
	}
	emails = [
		('google', ('gmail', 'googlemail')),
		('microsoft', ('hotmail', 'live', 'msn', 'sympatico', 'passport')),
		('yahoo', ('yahoo', 'rogers')),
	]
	


class OpenIDDBStore(openid.store.interface.OpenIDStore):
	def __init__(self, context):
#		self.get_session = get_session
		db = context.get_instance(database.Database)
		self.db_session = db.session
		self.OpenIDAssoc = db.models.OpenIDAssoc
		self.OpenIDNonce = db.models.OpenIDNonce
		self.context = context
	
	def get_session(self):
		self.context.logger.debug('Flushing session')
		self.db_session.flush()
		return self.db_session	
	
	def storeAssociation(self, server_url, association):
		self.context.logger.debug(u'Store association %s:%s', server_url, association)
		
		sess = self.get_session()
		assoc = self.OpenIDAssoc()
		assoc.server_url = server_url
		assoc.handle = association.handle
		assoc.secret = association.secret
		assoc.issued = association.issued
		assoc.lifetime = association.lifetime
		assoc.assoc_type = association.assoc_type
		sess.add(assoc)
		sess.flush()
	
	def getAssociation(self, server_url, handle=None):
		self.context.logger.debug(u'Get association %s:%s', server_url, handle)
		
		sess = self.get_session()
		if handle is None:
			r = sess.query(self.OpenIDAssoc)\
				.filter(self.OpenIDAssoc.server_url==server_url)
		else:
			r = sess.query(self.OpenIDAssoc)\
				.filter(self.OpenIDAssoc.server_url==server_url)\
				.filter(self.OpenIDAssoc.handle==handle)
		
		valid_assocs = []
		time_now = time.time()
		for assoc in r:
			if assoc.issued + assoc.lifetime < time_now:
				self.context.logger.debug(u'Deleting assoc %s', assoc)
				sess.delete(assoc)
			else:
				self.context.logger.debug(u'Valid assoc %s', assoc)
				valid_assocs.append(assoc)
		
		valid_assoc_objs = []
		
		for assoc in valid_assocs:
			valid_assoc_objs.append(openid.association.Association(
				assoc.handle, assoc.secret, assoc.issued, assoc.lifetime, 
				assoc.assoc_type))
		
		sess.flush()
		
		if valid_assoc_objs:
			return valid_assoc_objs[-1]
	
	def removeAssociation(self, server_url, handle):
		self.context.logger.debug(u'Remove association %s:%s', server_url, handle)
		
		sess = self.get_session()
		
		r = sess.query(self.OpenIDAssoc)\
			.filter(self.OpenIDAssoc.server_url==server_url)\
			.filter(self.OpenIDAssoc.handle==handle)
		
		for o in r:
			self.context.logger.debug(u'Deleting assoc %s', o)
			sess.delete(o)
		
		ans = r.count() > 0
		sess.flush()
		
		return ans
	
	def useNonce(self, server_url, timestamp, salt):
		self.context.logger.debug(u'Use nonce %s:%s:%s', server_url, timestamp, salt)
		
		if abs(timestamp - time.time()) > openid.store.nonce.SKEW:
			logger.debug(u'\t…false')
			return False
		
		sess = self.get_session()
		
		nonce = self.OpenIDNonce()
		nonce.server_url = server_url
		nonce.timestamp = timestamp
		nonce.salt = salt
		
		try:
			sess.add(nonce)
		except sqlalchemy.exc.IntegrityError:
			self.context.logger.debug(u'\t… Integrity error ')
			return False
		
		sess.flush()
		
		return True
	
	def cleanupNonces(self):
		self.context.logger.debug(u'Cleanup nonces')
		
		sess = self.get_session()
		
		q = sess.query(self.OpenIDNonce)\
			.filter(self.OpenIDNonce.lifetime < time.time())
		
		count = 0
		for o in q:
			self.context.logger.debug(u'Delete %s', o)
			sess.delete(o)
			count += 1
		
		sess.flush()
		
		return count
		
	def cleanupAssociations(self):
		self.context.logger.debug(u'Cleanup assocs')
		sess = self.get_session()
		
		q = sess.query(self.OpenIDAssoc)\
			.filter(self.OpenIDAssoc.issued + self.OpenIDAssoc.lifetime > time.time())
		
		count = 0
		for o in q:
			self.context.logger.debug(u'Delete %s', o)
			sess.delete(o)
			count += 1
		
		sess.flush()
		
		return count

class AccountRoleConfig(object):
	def __init__(self, namespace):
		self.namespace = namespace
		self.roles = []
	
	def add(self, code, label=None):
		self.roles.append((code, label))

class Accounts(base.BaseComponent):
	default_config = configloader.DefaultSectionConfig('accounts',
		master_test_password_salt=0,
		master_test_password_sha256_hex=0,
		master_test_username='root',
	)
	
	def init(self):
		db = self.context.get_instance(database.Database)
		db.add(AccountsMeta, AccountLogsMeta, OpenIDAssocMeta, OpenIDNonceMeta)
		self._roles = set()
		self._testing_account_sign_in_rate_limiter = [0, 0]
		
		if self.context.config.accounts.master_test_username:
			self._has_test_account_setup = False
		else:
			self._has_test_account_setup = True
		
	def setup(self):
		if not self.singleton._has_test_account_setup:
			db = self.context.get_instance(database.Database)
			username = self.context.config.accounts.master_test_username
			query = db.session.query(db.models.Account).filter_by(
				username=username)
		
			if not query.first() and username:
				model = db.models.Account(username=username)
				db.session.add(model)
			
			self.singleton._has_test_account_setup = True
		
		sess = self.context.get_instance(session.Session)
		self._account_id = sess.data._accounts_account_id
	
	def register_role(self, namespace, *roles):
		for role in roles:
			self.singleton._roles.add((namespace, role, None))
	
	def register_role_config(self, role_config):
		for code, label in role_config.roles:
			self.singleton._roles.add((role_config.namespace, code, label))
	
	def is_authenticated(self):
		return self._account_id is not None
	
	def is_authorized(self, namespace, role_code):
		if not self.is_authenticated:
			return False
		
		model = self.get_account_model(self.account_id)
		
		if not model:
			return False
		
		return (namespace, role_code) in model.roles
	
	@property
	def account_id(self):
		return self._account_id
	
	@property
	def account_model(self):
		if self.account_id:
			db = self.context.get_instance(database.Database)
			query = db.session.query(db.models.Account).filter_by(
				id=self.account_id)
			return query.first()
	
	def authenticate_openid_stage_1(self, openid_url, return_to_url):
		sess = self.context.get_instance(session.Session)
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
		db = self.context.get_instance(database.Database)
		
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
		self.context.logger.debug(u'Apply account id %s', account_id)
		self._account_id = account_id
		sess = self.context.get_instance(session.Session)
		sess.data._accounts_account_id = account_id
		
		model = self.get_account_model(account_id)
		
		if not model.sessions:
			model.sessions = self._session_data_template()
		
		event = {'ip': self.context.environ.get('REMOTE_ADDR'),
			'prev_acc': self.account_id,
		}
		
		self.log_event(AccountLogsMeta.NS_ACCOUNTS, 
			AccountLogsMeta.CODE_SESSION_ACTIVATE, info=event)
	
	def _session_data_template(self):
		d = {'date': time.time()}
		return d
	
	def log_event(self, namespace, code, info=None):
		db = self.context.get_instance(database.Database)
		log_model = db.models.AccountLog()
		log_model.account_id = self.account_id
		log_model.namespace = namespace
		log_model.action_code = code
		log_model.info = info
		db.session.add(log_model)
	
	def cancel_account_id(self):
		self.context.logger.debug(u'Cancel account id %s', self._account_id)
		
		event = {'ip': self.context.environ.get('REMOTE_ADDR'),
			'prev_acc': self.account_id,
		}
		
		self.log_event(AccountLogsMeta.NS_ACCOUNTS, 
			AccountLogsMeta.CODE_SESSION_DEACTIVATE, info=event)
		
		self._account_id = None
		sess = self.context.get_instance(session.Session)
		del sess.data._accounts_account_id
		
	
	def get_account_model(self, account_id):
		db = self.context.get_instance(database.Database)
		query = db.session.query(db.models.Account).filter_by(id=account_id)
		
		return query.first()
	
	def serve(self, success_redirect_url=None):
		doc = self.context.get_instance(wui.Document)
		if self.context.request.args:
			action = self.context.request.args[0]
		else:
			action = None
		
		self.context.response.ok()
		
		if action == 'edit':
			if self._check_perm():
				return
			
			self._serve_account_edit()
		elif action == 'list':
			doc.meta.title = 'Listing users'
			if self._check_perm():
				return
			
			self._serve_list()
		elif action == 'signout':
			doc.meta.title = 'Sign out'
			self.cancel_account_id()
			doc.add_message('You are now signed out')
		else:
			doc.meta.title = 'Sign in'
			
			root_password = self.context.request.form.getfirst('root')
			openid_url = self.context.request.form.getfirst('openid')
			provider = self.context.request.form.getfirst('provider')
			username = self.context.request.form.getfirst('username')
			
			dest_url = self.context.str_url(fill_controller=True,
				fill_args=True, params='openidphase2', fill_host=True)
			
			if root_password:
				
				if time.time() < self.singleton._testing_account_sign_in_rate_limiter[1]:
					self.context.response.set_status(403)
					doc.add_message('Rate limit exceeded')
					return
				
				self.authenticate_testing_password(root_password)
				
				if not self.is_authenticated():
					self.singleton._testing_account_sign_in_rate_limiter[0] += 1
					self.singleton._testing_account_sign_in_rate_limiter[1] = time.time() + 10 * self.singleton._testing_account_sign_in_rate_limiter[0]
				else:
					self.singleton._testing_account_sign_in_rate_limiter = [0, 0]
			
			elif openid_url:
				return self.context.response.redirect(
					self.authenticate_openid_stage_1(openid_url, dest_url), 303)
				
			elif provider:
				provider_url = OpenIDInfo.providers[provider][0]
				openid_url = provider_url
				
				if provider_url.find('{{}}') != -1:
					openid_url = provider_url.replace('{{}}', username)
				
				return self.context.response.redirect(
					self.authenticate_openid_stage_1(openid_url, dest_url), 303)
			
			elif self.context.request.params == 'openidphase2':
				display_name, openid_id, result_code = self.authenticate_openid_stage_2()
				db = self.context.get_instance(database.Database)
				
				if openid_id:
					query = db.session.query(db.models.Account) \
						.filter_by(username=openid_id)
					
					account_model = query.first()
					
					if not account_model:
						account_model = db.models.Account()
						account_model.username = openid_id
						account_model.nickname = display_name
						db.session.add(account_model)
						db.session.flush()
					
					self.apply_account_id(account_model.id) 
					
					doc.add_message('You are now signed in', u'Hello %s' % display_name)
				else:
					doc.add_message('Sorry, there was a problem during the sign in process',
						'Please try again later. (Error code %s' % result_code)

			
			if self.is_authenticated():
				doc.add_message('You are now signed in')
				
				nav = models.Nav()
				nav.add('Browse users', self.context.str_url(fill_controller=True,
					args=('list',)))
				doc.append(dataobject.MVPair(nav))
				
				if success_redirect_url:
					return self.context.response.redirect(success_redirect_url, 303)
				
				return
			
			doc.append(dataobject.MVPair(AccountSignInModel()))
			
		
	def _check_perm(self):
		if not self.account_model or self.account_model.username != self.context.config.accounts.master_test_username:
			self.context.response.set_status(403)
			return True
		
		return False
	
	def _serve_list(self):
		db = self.context.get_instance(database.Database)
		page_info = self.context.page_info()
		table = models.Table()
		table.header = ('ID', 'Username', 'Roles', 'Sessions', 'Profile')
		
		search_name = self.context.request.query.getfirst('search-name')
		
		query = db.session.query(db.models.Account) \
		
		if search_name:
			query = query.filter(db.models.Account.username.like(u'%s%%' % search_name))
		
		query = query.limit(page_info.limit + 1).offset(page_info.offset)
		
		form = models.Form()
		form.textbox('search-name', 'Search username')
		form.button('submit', 'Search')
		
		counter = 0
		for result in query:
			url = self.context.str_url(fill_controller=True,
				args=('edit', str(result.id))
			)
			
			table.rows.append([
				(str(result.id), url),
				result.username,
				unicode(result.roles),
				unicode(result.sessions),
				unicode(result.profile_data),
			])
			
			if counter > page_info.limit:
				page_info.more = True
		
		doc = self.context.get_instance(wui.Document)
		doc.append(dataobject.MVPair(form))
		doc.append(dataobject.MVPair(table, 
			row_views=(views.LabelURLToLinkView, None, None, None, None, None)))
		doc.append(dataobject.MVPair(page_info, views.PagerView))
	
	def _serve_account_edit(self):
		doc = self.context.get_instance(wui.Document)
		db = self.context.get_instance(database.Database)
		account_id = self.context.request.args[1]
		
		account = db.session.query(db.models.Account) \
			.filter_by(id=account_id).first()
		
		if 'submit' in self.context.request.form:
			new_roles = set()
			
			for s in self.context.request.form.getlist('roles'):
				namespace, role = json.loads(s)
				new_roles.add((namespace, role))
		
			self.log_event(AccountLogsMeta.NS_ACCOUNTS,
				AccountLogsMeta.CODE_ROLE_MODIFY,
				{'ip': self.context.environ.get('REMOTE_ADDR'),
				'new': list(new_roles)
				},
			)
			
			account.roles = new_roles
			
			doc.add_message('Account saved', str(new_roles))
			
			return
		
		form = models.Form(method=models.Form.POST)
		opts = form.options('roles', 'Roles', True)
		
		for namespace, role, label in self.singleton._roles:
			active = (namespace, role) in account.roles
			
			opts.option(json.dumps([namespace, role]), 
				u'%s %s (%s)' % (namespace, role, label),
				active)
		
		form.button('submit', 'Save')
		
		doc.title = u'Edit %s' % account.username
		doc.append(dataobject.MVPair(form))
	

class AccountSignInModel(dataobject.BaseModel):
	class default_view(dataobject.BaseView):
		@classmethod
		def to_html(cls, context, model):
			element = lxmlbuilder.DIV(ID='accounts-sign-in-wrapper')
			
			div = lxmlbuilder.DIV(lxmlbuilder.H3('OpenID'))
			form = models.Form(method=models.Form.POST)
			form.textbox('openid', 'OpenID')
			form.button('submit', 'Sign in')
			div.append(dataobject.MVPair(form).render(context, format='html'))
			
			element.append(div)
			
			l = sorted(OpenIDInfo.providers.iteritems(), key=lambda i:i[0])
			for provider, provider_data in l:
				url, name = provider_data
				div = lxmlbuilder.DIV(lxmlbuilder.H3(name))
				
				form = models.Form(method=models.Form.POST)
				form.textbox('provider', provider, validation=form.Textbox.HIDDEN)
				
				if url.find('{{}}') != -1:
					form.textbox('username', u'Username', required=True)
				
				form.button('submit', u'Sign in via %s' % name)
				
				div.append(dataobject.MVPair(form).render(context, format='html'))
				element.append(div)
			
			div = lxmlbuilder.DIV(lxmlbuilder.H3('root'))
			form = models.Form(method=models.Form.POST)
			form.textbox('root', 'Password', 
				validation=models.Form.Textbox.PASSWORD)
			form.button('submit', 'Sign in')
			div.append(dataobject.MVPair(form).render(context, format='html'))
			element.append(div)
			
			return element
			

def guess_provider_from_email(s):
	for provider, substrings in OpenIDInfo.emails.iteritems():
		for substring in substrings:
			if s.find(substring) != -1:
				return provider

__all__ = ('Accounts', 'AccountsMeta', 'AccountLogsMeta', 'AccountRoleConfig')
