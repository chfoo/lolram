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

from lolram_deprecated_1 import mylogger, configloader
from lolram_deprecated_1.components import base
from sqlalchemy.schema import Column
from sqlalchemy.types import Integer, DateTime, Text
import datetime
import imp
import os.path
import sqlalchemy.engine.url
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import sqlamp

__docformat__ = 'restructuredtext en'

_logger = mylogger.get_logger()

Base = sqlalchemy.ext.declarative.declarative_base()

class Database(base.BaseComponent):
	'''Database component'''
	
	default_config = configloader.DefaultSectionConfig('database',
		driver='sqlite', user=None, password=None, host=None, name='db.sqlite',
		port=None, automigrate=True, 
		)
	
	def init(self):
		conf = self.context.config.database
		
		if conf.driver == 'sqlite': 
			db_name = os.path.join(self.context.dirinfo.db, conf.name)
		else:
			db_name = conf.name
		
		db_url = sqlalchemy.engine.url.URL(drivername=conf.driver,
			username=conf.user, password=conf.password, host=conf.host,
			port=conf.port, database=db_name)
		
		_logger.info('Using SQLAlchemy DB URL %s', db_url)
		engine = sqlalchemy.create_engine(db_url)
		Session = sqlalchemy.orm.sessionmaker()
		Session.configure(bind=engine)
		table_meta_list = []
		models = imp.new_module('dbmodels')
		
		DatabaseTableMigration.metadata.create_all(bind=engine)
		
		self._engine = engine
		self._Session = Session
		self._models = models
		self._table_meta_list = table_meta_list
		self._migrated = False
		
	def migrate(self):
		_logger.info(u'Begin migrate')
		session = self.singleton._Session()
		for table_meta in self._table_meta_list:
			table_meta.migrate(self.engine, session)
		session.commit()
		session.close()
		_logger.info(u'End migrate')
	
	def add(self, *table_meta_classes):
		for table_meta_class in table_meta_classes:
			assert issubclass(table_meta_class, TableMeta)
			assert table_meta_class.uuid
			assert table_meta_class.defs
			assert isinstance(table_meta_class.defs, tuple) or isinstance(table_meta_class.defs, list)
			table_meta = table_meta_class()
			
			_logger.debug(u'Add table meta ‘%s’', table_meta.__class__.__name__)
			self.singleton._table_meta_list.append(table_meta)
			model = table_meta.get()
			name = model.__class__.__name__
			if name == 'DeclarativeMeta':
				name = str(model).rsplit('.', 1)[-1].rsplit("'", 1)[0]
			_logger.debug(u'Add model ‘%s’', name)
			model.metadata.bind = self.engine
			setattr(self.models, name, model)
			
			if self.context.config.automigrate:
				table_meta.migrate(self.engine, self.get_new_session())
	
	@property
	def models(self):
		return self.singleton._models
	
	@property
	def session(self):
		return self._session
	
	@property
	def engine(self):
		return self.singleton._engine
	
	@property
	def metadata(self):
		return DatabaseTableMigration.metadata
	
	def setup(self):
		if not self.singleton._migrated:
			self.singleton._migrated = True
			self.singleton.migrate()
		
		_logger.debug('New db session')
		self._session = self.singleton._Session()
	
	def cleanup(self):
		if self.context.errors:
			_logger.debug('DB rollback')
			self._session.rollback()
		else:
			_logger.debug('DB Commit')
			self._session.commit()
		
		self._session.close()


class DatabaseTableMigration(Base):
	'''Database model of for migrating tables'''
	
	__tablename__ = 'database_table_migrations'
	
	id = Column(Integer, primary_key=True)
	uuid = Column(Text, nullable=False, index=True)
	version = Column(Integer, nullable=False, default=-1)
	created = Column(DateTime, default=datetime.datetime.utcnow)
	modified = Column(DateTime, default=datetime.datetime.utcnow,
		onupdate=datetime.datetime.utcnow)


class TableMeta(object):
	'''Base class for table migration and definitions'''
	
	uuid = NotImplemented
	defs = []
	
	class Def(object):
		'''Base class for table migration'''
		
		desc = NotImplemented
		model = None
		table = None
		
		@staticmethod
		def base():
			'''SQLAlchemy base class for table model'''
			metadata = sqlalchemy.schema.MetaData()
			Base_ = sqlalchemy.ext.declarative.declarative_base(
				metaclass=sqlamp.DeclarativeMeta
			)
			return Base_
		
		def upgrade(self, engine, session):
			raise NotImplementedError()
		
		def downgrade(self, engine, session):
			raise NotImplementedError()
	
	def __init__(self):
		assert self.uuid is not NotImplemented
	
	def migrate(self, engine, session, version=None):
		_logger.debug(u'Table data versions %s', len(self.defs) - 1)
		
		if version is None:
			version = len(self.defs) - 1
		
		version = max(min(version, len(self.defs) - 1), -1)
		db_version = -1
		query = session.query(DatabaseTableMigration).filter_by(uuid=self.uuid)
		model = query.first()
		
		if model:
			db_version = model.version
		else:
			model = DatabaseTableMigration(uuid=self.uuid)
			session.add(model)
		
		_logger.info(u'Database migration for %s:%s from %s to %s',
			self, self.uuid, db_version, version)
		
		if db_version < version:
			new_version = db_version + 1
			
			_logger.debug(u'Upgrading %s→%s', db_version, new_version)
			self.defs[new_version]().upgrade(engine, session)
		elif db_version > version:
			_logger.debug(u'Downgrading %s', db_version)
			self.defs[db_version]().downgrade(engine, session)
			new_version = db_version - 1
		else:
			_logger.debug(u'Migration done')
			return
		
		model.version = new_version
		
		_logger.debug(u'Committing')
		session.commit()
		_logger.debug(u'Recursive call')
		self.migrate(engine, session, version)
	
	def get_version(self, session):
		query = session.query(DatabaseTableMigration).filter_by(uuid=self.uuid)
		model = query.first()
		
		if model:
			return model.version
		else:
			return -1
		
	def get(self, version=None):
		if version is None:
			version = len(self.defs) -1
		
		return self.defs[version]().model or self.defs[version]().table

