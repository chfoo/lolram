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

__doctype__ = 'restructuredtext en'

import os
import hashlib
import datetime
import time
import json
import random

from sqlalchemy import *
from sqlalchemy.orm import relationship, synonym

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


class Accounts(base.BaseComponent):
	default_config = configloader.DefaultSectionConfig('accounts',
		master_test_password_salt=0,
		master_test_password_sha256_hex=0,
		master_test_username='root',
	)
	
	def init(self):
		db = self.context.get_instance(database.Database)
		db.add(AccountsMeta, AccountLogsMeta)
		self._roles = set()
		
	def setup(self):
		db = self.context.get_instance(database.Database)
		username = self.context.config.accounts.master_test_username
		query = db.session.query(db.models.Account).filter_by(
			username=username)
		
		if not query.first() and username:
			model = db.models.Account(username=username)
			db.session.add(model)
		
		sess = self.context.get_instance(session.Session)
		self._account_id = sess.data._accounts_account_id
	
	def register_role(self, namespace, *roles):
		for role in roles:
			self.singleton._roles.add((namespace, role))
	
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
	
	def authenticate_openid_stage_1(self, url):
		# TODO
		pass
	
	def authenticate_openid_stage_2(self, url):
		# TODO
		pass
	
	def authenticate_testing_password(self, password):
		db = self.context.get_instance(database.Database)
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
		self._account_id = None
		sess = self.context.get_instance(session.Session)
		del sess.data._accounts_account_id
		
		event = {'ip': self.context.environ.get('REMOTE_ADDR'),
			'prev_acc': self.account_id,
		}
		
		self.log_event(AccountLogsMeta.NS_ACCOUNTS, 
			AccountLogsMeta.CODE_SESSION_DEACTIVATE, info=event)
	
	def get_account_model(self, account_id):
		db = self.context.get_instance(database.Database)
		query = db.session.query(db.models.Account).filter_by(id=account_id)
		
		return query.first()
	
	def serve(self):
		
		if self.context.request.args:
			action = self.context.request.args[0]
		else:
			action = None
		
		self.context.response.ok()
		
		if action == 'edit':
			self._check_perm()
			self._serve_account_edit()
		elif action == 'list':
			self._check_perm()
			self._serve_list()
	
	def _check_perm(self):
		if not self.account_model or self.account_model.username != self.context.config.accounts.master_test_password:
			self.context.response.set_status(403)
			return
	
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
		
		for namespace, role in self.singleton._roles:
			active = (namespace, role) in self.singleton._roles
			
			opts.option(json.dumps([namespace, role]), 
				u'%s %s' % (namespace, role),
				active)
		
		form.button('submit', 'Save')
		
		doc.title = u'Edit %s' % account.username
		doc.append(dataobject.MVPair(form))

__all__ = ('Accounts', 'AccountsMeta', 'AccountLogsMeta',)
