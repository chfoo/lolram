# encoding=utf8

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

from lolram_deprecated_1.components import database
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import Integer, Unicode, LargeBinary, DateTime, \
	UnicodeText, String, Boolean
import datetime
import json
import openid.association
import openid.store.interface
import openid.store.nonce
import os
import sqlalchemy
import time

__docformat__ = 'restructuredtext en'


class AccountsMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class Account(database.TableMeta.Def.base()):
			__tablename__ = 'accounts'
			
			id = Column(Integer, primary_key=True) #@ReservedAssignment
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
				self.roles = self.roles | frozenset([(namespace, code)])
			
			def remove_role(self, namespace, code):
				self.roles = self.roles - frozenset([(namespace, code)])
			
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
			
			id = Column(Integer, primary_key=True) #@ReservedAssignment
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


class AccountCaptchaMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class AccountCaptcha(database.TableMeta.Def.base()):
			__tablename__ = 'account_captchas'
			
			id = Column(Integer, primary_key=True) #@ReservedAssignment
			key = Column(LargeBinary(length=4), default=lambda: os.urandom(4),
				nullable=False)
			created = Column(DateTime, default=datetime.datetime.utcnow)
			question = Column(Unicode(length=12), nullable=False)
			answer = Column(Unicode(length=12), nullable=False)
			valid = Column(Boolean, default=True, nullable=False)
		
		desc = 'new table'
		model = AccountCaptcha
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine) 
	
	uuid = 'urn:uuid:e7b83618-5eee-4a34-9550-92131513eeac'
	defs = [D1,]





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
			self.context.logger.debug(u'\t…false')
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
			.filter(self.OpenIDNonce.timestamp < time.time() - openid.store.nonce.SKEW)
		
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
