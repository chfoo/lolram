# encoding=utf8

'''Database testing'''

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

import unittest
import tempfile
import os
import os.path
import datetime

from sqlalchemy import *
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
import migrate.versioning.util
from migrate.changeset.schema import *

from lolram.components import database

class KittensMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class Kitten(database.TableMeta.Def.base()):
			__tablename__ = 'kittens'
			id = Column(Integer, primary_key=True)
			name = Column(Unicode)	
		
		desc = 'new table'
		model = Kitten
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)

	class D2(database.TableMeta.Def):
		class Kitten(database.TableMeta.Def.base()):
			__tablename__ = 'kittens'
			id = Column(Integer, primary_key=True)
			name = Column(Unicode)
			birthdate = Column(Date)	
		
		desc = 'add column birthdate'
		model = Kitten
		
		def upgrade(self, engine, session):
			self.model.metadata.bind = engine
			self.model.__table__.c.birthdate.create(self.model.__table__,
				alter_metadata=False)
		
		def downgrade(self, engine, session):
			self.model.metadata.bind = engine
			self.model.__table__.c.birthdate.drop(self.model.__table__,
				alter_metadata=False)
	
	uuid = u'58f6070f-5891-4817-9ac9-35deca38ab02'
	defs = (D1, D2, )

class TestDatabaseBareMigration(unittest.TestCase):
	def setUp(self):
		path = os.path.join(tempfile.gettempdir(), 
			'lolram-tests-test-database-migration.sqlite')
		url = URL('sqlite', database=path)
		engine = create_engine(url, echo=True)
		engine = migrate.versioning.util.construct_engine(engine)
		database.DatabaseTableMigration.metadata.create_all(bind=engine)
		Session = sessionmaker(bind=engine)
		session = Session()
		self.engine = engine
		self.session = session
		self.path = path
	
	def tearDown(self):
		os.remove(self.path)
	
	def test_upgrading(self):
		'''It should upgrade kitten'''
		kittens = KittensMeta()
		kittens.migrate(self.engine, self.session)
	
	def test_downgrading(self):
		'''It should downgrade kitten'''
		kittens = KittensMeta()
		kittens.migrate(self.engine, self.session)
		kittens.migrate(self.engine, self.session, version=-1)
	
	def test_upgrade_steps_and_insert(self):
		'''It should upgrade one level, insert data, 
		upgrade one level, and insert data'''
		
		kittens = KittensMeta()
		kittens.migrate(self.engine, self.session, version=0)
		kitten = kittens.get(0)()
		kitten.name = u'Maru'
		self.session.add(kitten)
		self.session.commit()
		self.assertTrue(kitten.id is not None)
		kittens.migrate(self.engine, self.session)
		query = self.session.query(kittens.get()).filter_by(name=u'Maru')
		kitten = query.first()
		self.assertTrue(kitten)
		kitten.birthdate = datetime.date(1990, 01, 01)
		self.session.commit()
		
