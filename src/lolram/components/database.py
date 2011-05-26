# encoding=utf8

'''Database'''

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

import imp
import os.path

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.engine.url

import base
from .. import configloader
from .. import mylogger
logger = mylogger.get_logger()
from lolram import database as database_module

class DatabaseAgent(base.BaseComponentAgent):
	def __init__(self, fardel, manager):
		self._manager = manager
	
	def setup(self, fardel):
		self._session = self._manager.get_new_session()
	
	def cleanup(self, fardel):
		logger.debug(u'Database commit')
		self._session.commit()
	
	@property
	def session(self):
		return self._session
	
	@property
	def engine(self):
		return self._manager.engine
	
	@property
	def models(self):
		return self._manager.models
	
	@property
	def metadata(self):
		return database_module.DatabaseTableMigration.metadata

class DatabaseManager(base.BaseComponentManager):
	default_config = configloader.DefaultSectionConfig('database',
		driver='sqlite', user=None, password=None, host=None, name='db.sqlite',
		port=None, automigrate=True, 
		)
	agent_class = DatabaseAgent
	name = 'database'
	
	def __init__(self, fardel):
		conf = fardel.conf.database
		if conf.driver == 'sqlite': 
			db_name = os.path.join(fardel.dirs.db, conf.name)
		else:
			db_name = conf.name
		db_url = sqlalchemy.engine.url.URL(drivername=conf.driver,
			username=conf.user, password=conf.password, host=conf.host,
			port=conf.port, database=db_name)
		logger.info('Using SQLAlchemy DB URL %s', db_url)
		engine = sqlalchemy.create_engine(db_url)
		Session = sqlalchemy.orm.sessionmaker()
		Session.configure(bind=engine)
		table_meta_list = []
		models = imp.new_module('dbmodels')
		
		database_module.DatabaseTableMigration.metadata.create_all(bind=engine)
		
		self._engine = engine
		self._Session = Session
		self._models = models
		self._table_meta_list = table_meta_list
		self._conf = conf
		self._fardel = fardel
		
	def migrate(self):
		logger.info(u'Begin migrate')
		for table_meta in self._table_meta_list:
			table_meta.migrate(self.engine, self.session)
		logger.info(u'End migrate')
	
	def add(self, table_meta):
		assert isinstance(table_meta, database_module.TableMeta)
		
		logger.debug(u'Add table meta ‘%s’', table_meta.__class__.__name__)
		self._table_meta_list.append(table_meta)
		model = table_meta.get()
		name = model.__class__.__name__
		if name == 'DeclarativeMeta':
			name = str(model).rsplit('.', 1)[-1].rsplit("'", 1)[0]
		logger.debug(u'Add model ‘%s’', name)
		model.metadata.bind = self._engine
		setattr(self._models, name, model)
		
		if self._conf.automigrate:
			table_meta.migrate(self.engine, self.get_new_session())
	
	@property
	def models(self):
		return self._models
	
	@property
	def engine(self):
		return self._engine
	
	def get_new_session(self):
		return self._Session()


