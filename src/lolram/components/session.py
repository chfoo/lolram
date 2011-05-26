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

__doctype__ = 'restructuredtext en'

import datetime
import base64
import time
import os
import json
import Cookie

from sqlalchemy import *
from sqlalchemy.orm import relationship

import base
from lolram import database
from lolram import configloader
from lolram import dataobject
from lolram import mylogger
logger = mylogger.get_logger()

class SessionSecretsDef_1(database.TableDef):
	class SessionSecret(database.TableDef.get_base()):
		__tablename__ = 'session_secrets'
		id = Column(Integer, primary_key=True)
		key = Column(LargeBinary(length=16), unique=True, nullable=False,
			index=True)
		created = Column(DateTime, default=datetime.datetime.utcnow)
	
	desc = 'new table'
	model = SessionSecret
	
	def upgrade(self, engine, session):
		self.SessionSecret.__table__.create(engine)
	
	def downgrade(self, engine, session):
		self.SessionSecret.__table__.drop(engine)

class SessionSecretsMeta(database.TableMeta):
	uuid = 'urn:uuid:a7df9e44-4c60-4589-8355-36abc8d5ddea'
	
	def init(self):
		self.push(SessionSecretsDef_1)

class SessionDataDef_1(database.TableDef):
	class SessionData(database.TableDef.get_base()):
		__tablename__ = 'session_data'
		
		id = Column(Integer, primary_key=True)
		perm_secret_id = Column(ForeignKey(SessionSecretsDef_1.SessionSecret.id),
			unique=True, nullable=True, index=True)
		perm_secret = relationship(SessionSecretsDef_1.SessionSecret, 
#			cascade='all, delete, delete-orphan',
			primaryjoin=perm_secret_id==SessionSecretsDef_1.SessionSecret.id)
		temp_secret_id = Column(ForeignKey(SessionSecretsDef_1.SessionSecret.id),
			unique=True, nullable=False, index=True)
		temp_secret = relationship(SessionSecretsDef_1.SessionSecret,
#			cascade='all, delete, delete-orphan',
			primaryjoin=temp_secret_id==SessionSecretsDef_1.SessionSecret.id)
		data = Column(Unicode)
		created = Column(DateTime, default=datetime.datetime.utcnow)
		modified = Column(DateTime, default=datetime.datetime.utcnow,
			onupdate=datetime.datetime.utcnow)
	
	desc = 'new table'
	model = SessionData
	
	def upgrade(self, engine, session):
		self.SessionData.__table__.create(engine)
	
	def downgrade(self, engine, session):
		self.SessionData.__table__.drop(engine)

class SessionDataMeta(database.TableMeta):
	uuid = 'urn:uuid:38a4d8d3-e615-422d-a92c-c8de67197ee9'
	
	def init(self):
		self.push(SessionDataDef_1)

class SessionAgent(base.BaseComponentAgent):
	def __init__(self, fardel, manager):
		self._manager = manager
	
	def setup(self, fardel):
		self._data, self._persistent = self._manager.get_session(fardel)
	
	def cleanup(self, fardel):
		self._manager.save_session(fardel, self._data, self._persistent)
	
	@property
	def persistent(self):
		return self._persistent
	
	@persistent.setter
	def persistent(self, v):
		self._persistent = v
	
	@property
	def data(self):
		return self._data 

class SessionManager(base.BaseComponentManager):
	default_config = configloader.DefaultSectionConfig('session',
		perm_cookie_name='lolramsid',
		temp_cookie_name='lolramsidt',
		cookie_max_age=23667695,
		key_rotation_age=86400, # 1 day
		key_max_age=1209600, # 2 weeks
		key_stale_age=23667695, # 9 months
	)
	name = 'session'
	agent_class = SessionAgent
	
	def __init__(self, fardel):
		fardel.component_managers.database.add(SessionDataMeta())
		fardel.component_managers.database.add(SessionSecretsMeta())
	
	def perform_maintenance(self, fardel):
		self.clear_stale_sessions(fardel)
	
	def set_cookie(self, fardel, name, value, max_age=None):
		logger.debug(u'Set cookie %s', name)
		
		cookie_obj = Cookie.SimpleCookie()
		cookie_obj[name] = value
		
		if max_age is not None:
			cookie_obj[name]['max-age'] = max_age
			
		cookie_obj[name]['path'] = u'/%s' % fardel.req.script_name
		cookie_obj[name]['httponly'] = 'HttpOnly'
		
		fardel.resp.headers.add('set-cookie', 
			cookie_obj.output(header='', sep=''))
			
	def get_session(self, fardel):
		logger.debug(u'Get session')
		
		header_value = fardel.req.headers.get('cookie')
		
		perm_name = fardel.conf.session.perm_cookie_name
		temp_name = fardel.conf.session.temp_cookie_name
		session_data = dataobject.DataObject()
		persistent = False
		
		if header_value:
			cookie_obj = Cookie.SimpleCookie()
			cookie_obj.load(header_value)
			
			perm_key = None
			temp_key = None
			
			if perm_name in cookie_obj:
				morsel = cookie_obj[perm_name]
				try:
					perm_key = base64.b64decode(morsel.value)
					logger.debug(u'Got perm key')
				except TypeError:
					pass
			
			if temp_name in cookie_obj:
				morsel = cookie_obj[temp_name]
				try:
					temp_key = base64.b64decode(morsel.value)
					logger.debug(u'Got temp key')
				except TypeError:
					pass
			
			key_max_date = datetime.datetime.utcfromtimestamp(
				time.time() - fardel.conf.session.key_max_age)
			
			query = fardel.database.session.query(fardel.database.models.SessionData) \
				.filter(fardel.database.models.SessionSecret.key==temp_key) \
				.filter(
					fardel.database.models.SessionSecret.id== \
					fardel.database.models.SessionData.temp_secret_id) \
				.filter(fardel.database.models.SessionSecret.created>key_max_date)
			model = query.first()
			
			if not model:
				query = fardel.database.session.query(fardel.database.models.SessionData) \
					.filter(fardel.database.models.SessionSecret.key==temp_key) \
					.filter(
						fardel.database.models.SessionSecret.id== \
						fardel.database.models.SessionData.temp_secret_id) \
					.filter(fardel.database.models.SessionSecret.created>key_max_date)
				model = query.first()
			
			if model:
				session_data = dataobject.DataObject(json.loads(model.data))
				session_data.__.id = model.id
				logger.debug(u'Session found ‘%s’', model.id)
				persistent =  model.perm_secret is not None
		
		return (session_data, persistent)
	
	def save_session(self, fardel, data, persistent=False):
		logger.debug(u'Save session')
		
		model = None
		perm_name = fardel.conf.session.perm_cookie_name
		temp_name = fardel.conf.session.temp_cookie_name
		
		if getattr(data.__, 'id', None) is not None:
			query = fardel.database.session.query(fardel.database.models.SessionData) \
				.filter_by(id=data.__.id)
			
			model = query.first()
			
			if not data:
				logger.debug(u'Empty data and model. Remove from db.')
				fardel.database.session.delete(model)
		
		if not data:
			logger.debug(u'Session data empty. Early return')
			return
		
		if not model:
			model = fardel.database.models.SessionData()
			fardel.database.session.add(model)
		
		model.data = json.dumps(data)
		
		key_rotation_date = datetime.datetime.utcfromtimestamp(
			time.time() - fardel.conf.session.key_rotation_age)
		
		if persistent:
			if not model.perm_secret \
			or model.perm_secret and model.perm_secret.created < key_rotation_date:
				key_model = self.new_key(fardel)
				model.perm_secret = key_model
				self.set_cookie(fardel, perm_name, 
					base64.b64encode(key_model.key))
		else:
			if not model.temp_secret \
			or model.temp_secret and model.temp_secret.created < key_rotation_date:
				key_model = self.new_key(fardel)
				model.temp_secret = key_model
				self.set_cookie(fardel, temp_name, 
					base64.b64encode(key_model.key))
		
	def new_key(self, fardel):
		logger.debug(u'New key requested')
		bytes = os.urandom(16)
		model = fardel.database.models.SessionSecret()
		model.key = bytes
		fardel.database.session.add(model)
		return model
	
	def clear_stale_sessions(self, fardel):
		stale_date = datetime.datetime.utcfromtimestamp(
			time.time() - fardel.conf.session.key_stale_age)
		
		query = fardel.database.session.query(fardel.database.models.SessionSecrets) \
			.filter(fardel.database.models.SessionSecrets.modified<stale_date)
		
		query.delete()



