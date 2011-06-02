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

import hashlib
import datetime

from sqlalchemy import *
from sqlalchemy.orm import relationship

import base
from .. import dataobject
from .. import configloader
import database
import session

class AccountsMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class Account(database.TableMeta.Def.base()):
			__tablename__ = 'accounts'
			
			id = Column(Integer, primary_key=True)
			
		desc = 'new table'
		model = Account
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine) 
	
	uuid = 'urn:uuid:6f82230b-4f38-4e9f-b32c-6a877e8361bd'
	defs = (D1,)


class Accounts(base.BaseComponent):
	def init(self):
		db = self.context.get_instance(database.Database)
		db.add(AccountsMeta)
		
	def setup(self):
		sess = self.context.get_instance(session.Session)
		self._account_id = sess.data._accounts_account_id
	
	def is_authenticated(self):
		return self._account_id is not None
	
	def is_authorized(self, action):
		# TODO
		raise NotImplementedError()
	
	@property
	def account_id(self):
		return self._account_id
	
	def authenticate_openid_stage_1(self, url):
		# TODO
		pass
	
	def authenticate_openid_stage_2(self, url):
		# TODO
		pass
	
	def authenticate_testing_password(self, password):
		sha256_obj = hashlib.sha256(password)
		
		salt = self.context.config.accounts.master_test_password_salt
		
		if not salt:
			raise Exception('Salt not defined')
		
		sha256_obj.update(salt)
		
		hex1 = sha256_obj.hexdigest().lower()
		hex2 = self.context.config.accounts.master_test_password_sha256_hex
		
		if hex2 and hex1 == hex2.lower():
			self.apply_account_id(True)
		
		return self._account_id
	
	def apply_account_id(self, account_id):
		self.context.logger.debug(u'Apply account id %s', account_id)
		self._account_id = account_id
		sess = self.context.get_instance(session.Session)
		sess.data._accounts_account_id = account_id
	
	def cancel_account_id(self):
		self.context.logger.debug(u'Cancel account id %s', self._account_id)
		self._account_id = None
		sess = self.context.get_instance(session.Session)
		sess.data._accounts_account_id
