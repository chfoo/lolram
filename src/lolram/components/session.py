# encoding=utf8

'''Session'''

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

import datetime
import base64
import time
import os
import json
import Cookie

from sqlalchemy import *
from sqlalchemy.orm import relationship

import base
import database
from lolram import configloader
from lolram import dataobject


class SessionSecretsMeta(database.TableMeta):
	uuid = 'urn:uuid:a7df9e44-4c60-4589-8355-36abc8d5ddea'
	
	class D1(database.TableMeta.Def):
		class SessionSecret(database.TableMeta.Def.base()):
			__tablename__ = 'session_secrets'
			
			id = Column(Integer, primary_key=True)
			key = Column(LargeBinary(length=16), unique=True, nullable=False)
			created = Column(DateTime, default=datetime.datetime.utcnow)
		
		desc = 'new table'
		model = SessionSecret
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)
	
	defs = (D1,)

class SessionDataMeta(database.TableMeta):
	uuid = 'urn:uuid:38a4d8d3-e615-422d-a92c-c8de67197ee9'
	
	class D1(database.TableMeta.Def):
		class SessionData(database.TableMeta.Def.base()):
			__tablename__ = 'session_data'
			
			id = Column(Integer, primary_key=True)
			perm_secret_id = Column(
				ForeignKey(SessionSecretsMeta.D1.SessionSecret.id),
				unique=True, nullable=True, index=True)
			perm_secret = relationship(SessionSecretsMeta.D1.SessionSecret, 
	#			cascade='all, delete, delete-orphan',
				primaryjoin=perm_secret_id==SessionSecretsMeta.D1.SessionSecret.id)
			temp_secret_id = Column(
				ForeignKey(SessionSecretsMeta.D1.SessionSecret.id),
				unique=True, nullable=False, index=True)
			temp_secret = relationship(SessionSecretsMeta.D1.SessionSecret,
	#			cascade='all, delete, delete-orphan',
				primaryjoin=temp_secret_id==SessionSecretsMeta.D1.SessionSecret.id)
			data = Column(Unicode)
			created = Column(DateTime, default=datetime.datetime.utcnow)
			modified = Column(DateTime, default=datetime.datetime.utcnow,
				onupdate=datetime.datetime.utcnow)
		
		desc = 'new table'
		model = SessionData
	
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)
	
	defs = (D1,)

class Session(base.BaseComponent):
	default_config = configloader.DefaultSectionConfig('session',
		perm_cookie_name='lolramsid',
		temp_cookie_name='lolramsidt',
		cookie_max_age=23667695,
		key_rotation_age=86400, # 1 day
		key_max_age=1209600, # 2 weeks
		key_stale_age=23667695, # 9 months
	)
	
	def setup(self):
		self._data, self._persistent = self._get_session()
	
	def cleanup(self):
		self._save_session(self._data, self._persistent)
	
	@property
	def persistent(self):
		return self._persistent
	
	@persistent.setter
	def persistent(self, v):
		self._persistent = v
	
	@property
	def data(self):
		return self._data 
	
	def init(self):
		db = self.context.get_instance(database.Database)
		map(lambda m: db.add(m), (SessionDataMeta, SessionSecretsMeta))
	
	def run_maintenance(self):
		self._clear_stale_sessions()
	
	def _set_cookie(self, name, value, max_age=None):
		self.context.logger.debug(u'Set cookie %s', name)
		
		cookie_obj = Cookie.SimpleCookie()
		cookie_obj[name] = value
		
		if max_age is not None:
			cookie_obj[name]['max-age'] = max_age
			
		cookie_obj[name]['path'] = u'/%s' % self.context.request.script_path
		cookie_obj[name]['httponly'] = 'HttpOnly'
		
		self.context.response.headers.add('set-cookie', 
			cookie_obj.output(header='', sep=''))
	
	def _get_session(self):
		db = self.context.get_instance(database.Database)
		self.context.logger.debug(u'Get session')
		
		header_value = self.context.request.headers.get('cookie')
		
		perm_name = self.context.config.session.perm_cookie_name
		temp_name = self.context.config.session.temp_cookie_name
		session_data = dataobject.DataObject()
		persistent = False
		
		if header_value:
			cookie_obj = Cookie.SimpleCookie()
			cookie_obj.load(header_value)
			
			def get_key(name):
				if name in cookie_obj:
					morsel = cookie_obj[name]
					try:
						id_, key = json.loads(base64.b64decode(morsel.value))
						key = key.decode('base64')
						self.context.logger.debug(u'Got %s key %s', name, id_)
						return (id_, key)
					except TypeError:
						pass
					except ValueError:
						pass
				
				return (None, None)
			
			perm_id, perm_key = get_key(perm_name)
			temp_id, temp_key = get_key(temp_name)
			
			key_max_date = datetime.datetime.utcfromtimestamp(
				time.time() - self.context.config.session.key_max_age)
			
			model = None
			
			if temp_id:
				query = db.session.query(db.models.SessionData) \
					.filter(db.models.SessionSecret.key==temp_key) \
					.filter(db.models.SessionSecret.id==temp_id) \
					.filter(db.models.SessionSecret.created>key_max_date) \
					.filter(temp_id==db.models.SessionData.temp_secret_id)
				model = query.first()
					
			if not model and perm_id:
				query = db.session.query(db.models.SessionData) \
					.filter(db.models.SessionSecret.key==perm_key) \
					.filter(db.models.SessionSecret.id==perm_id) \
					.filter(db.models.SessionSecret.created>key_max_date) \
					.filter(perm_id==db.models.SessionData.perm_secret_id)
				model = query.first()
			
			if model:
				session_data = dataobject.DataObject(json.loads(model.data))
				session_data.__.id = model.id
				self.context.logger.debug(u'Session found ‘%s’', model.id)
				persistent =  model.perm_secret is not None
		
		return (session_data, persistent)
	
	def _save_session(self, data, persistent=False):
		db = self.context.get_instance(database.Database)
		self.context.logger.debug(u'Save session')
		
		model = None
		perm_name = self.context.config.session.perm_cookie_name
		temp_name = self.context.config.session.temp_cookie_name
		
		if getattr(data.__, 'id', None) is not None:
			query = db.session.query(db.models.SessionData) \
				.filter_by(id=data.__.id)
			
			model = query.first()
			
			if not data:
				self.context.logger.debug(u'Empty data and model. Remove from db.')
				db.session.delete(model)
		
		if not data:
			self.context.logger.debug(u'Session data empty. Early return')
			return
		
		if not model:
			model = db.models.SessionData()
			db.session.add(model)
		
		model.data = json.dumps(data)
		
		key_rotation_date = datetime.datetime.utcfromtimestamp(
			time.time() - self.context.config.session.key_rotation_age)
		
		if persistent:
			if not model.perm_secret \
			or model.perm_secret and model.perm_secret.created < key_rotation_date:
				key_model = self._new_key()
				model.perm_secret = key_model
				db.session.flush()
				self._set_cookie(perm_name, base64.b64encode(json.dumps([key_model.id, key_model.key.encode('base64')])))
		else:
			if not model.temp_secret \
			or model.temp_secret and model.temp_secret.created < key_rotation_date:
				key_model = self._new_key()
				model.temp_secret = key_model
				db.session.flush()
				self._set_cookie(temp_name, base64.b64encode(json.dumps([key_model.id, key_model.key.encode('base64')])))
		
	def _new_key(self):
		db = self.context.get_instance(database.Database)
		self.context.logger.debug(u'New key requested')
		bytes = os.urandom(16)
		model = db.models.SessionSecret()
		model.key = bytes
		db.session.add(model)
		return model
	
	def _clear_stale_sessions(self):
		db = self.context.get_instance(database.Database)
		stale_date = datetime.datetime.utcfromtimestamp(
			time.time() - self.context.config.session.key_stale_age)
		
		query = db.session.query(db.models.SessionSecret) \
			.filter(db.models.SessionSecret.created<stale_date)
		query.delete()
		
		query = db.session.query(db.models.SessionData) \
			.filter(db.models.SessionData.modified<stale_date)
		query.delete()
	
	@property
	def session_id(self):
		return getattr(self.data.__, 'id', None)
	
