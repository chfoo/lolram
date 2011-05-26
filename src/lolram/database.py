# encoding=utf8

'''Database'''

#	Copyright © 2010–2011 Christopher Foo <chris.foo@gmail.com>

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

from sqlalchemy import *
import sqlalchemy.ext.declarative
import sqlalchemy.schema

import mylogger
logger = mylogger.get_logger()

Base = sqlalchemy.ext.declarative.declarative_base()
class DatabaseTableMigration(Base):
	__tablename__ = 'database_table_migrations'
	
	id = Column(Integer, primary_key=True)
	uuid = Column(Text, nullable=False, index=True)
	version = Column(Integer, nullable=False, default=-1)
	created = Column(DateTime, default=datetime.datetime.utcnow)
	modified = Column(DateTime, default=datetime.datetime.utcnow,
		onupdate=datetime.datetime.utcnow)

class TableMeta(object):
	uuid = NotImplemented
	
	def __init__(self):
		self.data = []
		self.init()
		assert self.uuid is not NotImplemented
	
	def init(self):
		raise NotImplementedError()
	
	def push(self, d):
		assert issubclass(d, TableDef)
		assert d.model or d.table
		assert d.desc
		self.data.append(d)
	
	def migrate(self, engine, session, version=None):
		logger.debug(u'Table data versions %s', len(self.data) - 1)
		
		if version is None:
			version = len(self.data) - 1
		
		version = max(min(version, len(self.data) - 1), -1)
		db_version = -1
		query = session.query(DatabaseTableMigration).filter_by(uuid=self.uuid)
		model = query.first()
		
		if model:
			db_version = model.version
		else:
			model = DatabaseTableMigration(uuid=self.uuid)
			session.add(model)
		
		logger.info(u'Database migration for %s from %s to %s',
			self.uuid, db_version, version)
		
		if db_version < version:
			new_version = db_version + 1
			
			logger.debug(u'Upgrading %s→%s', db_version, new_version)
			self.data[new_version]().upgrade(engine, session)
		elif db_version > version:
			logger.debug(u'Downgrading %s', db_version)
			self.data[db_version]().downgrade(engine, session)
			new_version = db_version - 1
		else:
			logger.debug(u'Migration done')
			return
		
		model.version = new_version
		
		logger.debug(u'Committing')
		session.commit()
		logger.debug(u'Recursive call')
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
			version = len(self.data) -1
		
		return self.data[version]().model or self.data[version]().table

class TableDef(object):
	desc = NotImplemented
	model = None
	table = None
	
	@staticmethod
	def get_base():
		metadata = sqlalchemy.schema.MetaData()
		Base_ = sqlalchemy.ext.declarative.declarative_base()
		return Base_
	
	def upgrade(self, engine, session):
		raise NotImplementedError()
	
	def downgrade(self, engine, session):
		raise NotImplementedError()
	
