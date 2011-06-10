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

import dbutil.history_meta

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
			username = Column(Unicode(length=255), nullable=False, unique=True, 
				index=True)
			password = Column(LargeBinary(length=16))
			created = Column(DateTime, default=datetime.datetime.utcnow)
			modified = Column(DateTime, default=datetime.datetime.utcnow,
				onupdate=datetime.datetime.utcnow)
			nickname = Column(Unicode(length=160))
			attributes = Column(UnicodeText)
			
		desc = 'new table'
		model = Account
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine) 
	
	uuid = 'urn:uuid:6f82230b-4f38-4e9f-b32c-6a877e8361bd'
	defs = (D1,)

#class Account

class AccountRolesMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class AccountRole(database.TableMeta.Def.base()):
			__tablename__ = 'account_roles'
			
			id = Column(Integer, primary_key=True)
			namespace = Column(Unicode(length=255), nullable=False)
			role_code = Column(Integer, nullable=False)
			
		desc = 'new table'
		model = AccountRole
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine) 
			
	uuid = 'urn:uuid:d416a612-ea62-4c44-929a-84328bf80f97'
	defs = (D1,)

class AccountRoleMappingsMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class AccountRoleMapping(database.TableMeta.Def.base()):
			__tablename__ = 'account_role_mappings'
			
			id = Column(Integer, primary_key=True)
			account_id = Column(ForeignKey(AccountsMeta.D1.Account.id), 
				nullable=False, index=True)
			account = relationship(AccountsMeta.D1.Account, backref='roles')
			role_id = Column(ForeignKey(AccountRolesMeta.D1.AccountRole.id), 
				nullable=False)
			role = relationship(AccountRolesMeta.D1.AccountRole, 
				backref='accounts', collection_class=set)
			
		desc = 'new table'
		model = AccountRoleMapping
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine) 
			
	uuid = 'urn:uuid:bf81457a-e6d2-44ec-ab8f-0b473fc16c44'
	defs = (D1,)


class AccountLogsMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class AccountLog(database.TableMeta.Def.base()):
			__tablename__ = 'account_logs'
			
			id = Column(Integer, primary_key=True)
			account_id = Column(ForeignKey(AccountsMeta.D1.Account.id), 
				nullable=False)
			account = relationship(AccountsMeta.D1.Account, 
				primaryjoin=AccountsMeta.D1.Account.id==account_id)
			action_code = Column(Integer, nullable=False)
			created = Column(DateTime, default=datetime.datetime.utcnow)
			target_account_id = Column(ForeignKey(AccountsMeta.D1.Account.id))
			target_account = relationship(AccountsMeta.D1.Account, 
				primaryjoin=AccountsMeta.D1.Account.id==target_account_id)
			info_str = Column(Unicode(length=255))
			
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
	)
	
	APPLY_ACCOUNT_ID = 1
	CANCEL_ACCOUNT_ID = 2
	ROLE_MODIFY = 3
	
	def init(self):
		db = self.context.get_instance(database.Database)
		db.add(AccountsMeta)
		db.add(AccountRolesMeta)
		db.add(AccountRoleMappingsMeta)
		db.add(AccountLogsMeta)
		
	def setup(self):
		sess = self.context.get_instance(session.Session)
		self._account_id = sess.data._accounts_account_id
	
	def is_authenticated(self):
		return self._account_id is not None
	
	def is_authorized(self, namespace, role_code):
		for role in self.get_account_db_model().roles:
			if role.namespace == namespace and role.role_code == role_code:
				return True
	
	def get_account_roles(self):
		model = self.get_account_db_model()
		l = []
		for role in model.roles:
			l.append((role.namespace, role.role_code))
		
		return frozenset(l)
	
	def set_account_roles(self, i):
		pass
	
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
	
	def get_account_db_model(self):
		db = self.context.get_instance(database.Database)
		query = db.session.query('Accounts').filter_by(id=self.account_id)
		
		return query.first()

class Account(dataobject.ProtectedObject):
	pass