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
from .. import mylogger
logger = mylogger.get_logger()

class AccountsDef_1(database.TableDef):
	class Account(database.TableDef.get_base()):
		__tablename__ = 'accounts'
		
		id = Column(Integer, primary_key=True)
		
	desc = 'new table'
	model = Account
	
	def upgrade(self, engine, session):
		self.model.__table__.create(engine)
	
	def downgrade(self, engine, session):
		self.model.__table__.drop(engine) 


class AccountsMeta(database.TableMeta):
	uuid = 'urn:uuid:6f82230b-4f38-4e9f-b32c-6a877e8361bd'
	
	def init(self):
		self.push(AccountsDef_1)



