# encoding=utf8

'''Resource pooling system

The resource pool system stores a single copy of strings or files and returns
an unique
ID number for the given resource.
'''

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

import os
import shutil
import hashlib

from sqlalchemy import *

from lolram.components import database
from lolram.components import base
from lolram.components import cache
from lolram import util

class ResPoolTextMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class ResPoolText(database.TableMeta.Def.base()):
			__tablename__ = 'res_pool_text'
			
			id = Column(Integer, primary_key=True)
			text = Column(UnicodeText)
			hash = Column(LargeBinary(length=32), unique=True, index=True,
				nullable=False)
		
		desc = 'new table'
		model = ResPoolText
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)

	uuid = 'urn:uuid:6e8b3455-529c-484a-8437-c3239d28b296'
	
	defs = (D1,)


class ResPoolFileMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class ResPoolFile(database.TableMeta.Def.base()):
			__tablename__ = 'res_pool_file'
			
			id = Column(Integer, primary_key=True)
			hash = Column(LargeBinary(length=32), unique=True, index=True,
				nullable=False)
		
		desc = 'new table'
		model = ResPoolFile
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)

	uuid = 'urn:uuid:d63ebff1-a85d-4fdc-b1b2-6e702d1c23c1'
	
	defs = (D1,)


class ResPoolUnicodeType(unicode):
	__slots__ = ('hash',)


class ResPoolFileType(file):
	__slots__ = ('hash', 'filename')

class ResPoolFilenameType(unicode):
	__slots__ = ('hash')


class GlobalResPoolManager(base.BaseGlobalComponent):
	def init(self):
		db = self.context.get_instance(database.Database)
		db.add(ResPoolFileMeta)
		db.add(ResPoolTextMeta)

class ResPool(base.BaseComponent):
	'''The text pool interface component''' 
	
	__slots__ = ()
	
	FILE_MAX = 32 ** 8 - 1
	FILE_DIR_HASH = 997
	
	def __init__(self, *args, **kargs):
		super(ResPool, self).__init__(*args, **kargs)
		# FIXME: should be a seperate init function
		self._cache = cache.Cache(self.context)
	
	def _get_text_model(self, id):
		db = database.Database(self.context)
		query = db.session.query(db.models.ResPoolText)
		query = query.filter_by(id=id)
		return query.first()
	
	def _get_file_model(self, id):
		db = database.Database(self.context)
		query = db.session.query(db.models.ResPoolFile)
		query = query.filter_by(id=id)
		return query.first()
	
	def get_text(self, id):
		'''Get the text given the ID
		
		:rtype: `ResPoolUnicodeType`
		'''
		
		k = 'respool-text-%s' % id
		d = self._cache.get(k)
		
		if not d:
			model = self._get_text_model(id)
			
			if model:
				d = (model.text, model.hash)
				self._cache.set(k, d)
		
		if d:
			s = ResPoolUnicodeType(d[0])
			s.hash = d[1]
			
			return s
	
	def _get_file_path(self, id):
		assert isinstance(id, int)
		hash_val = str(id % self.FILE_DIR_HASH)
		filename = util.bytes_to_b32low(util.int_to_bytes(id))
		path = os.path.join(self.context.dirinfo.upload, hash_val, filename)
		return path
	
	def get_file(self, id):
		'''Get the file  given the ID
		
		:warning:
			Do not write to the file!
		
		:rtype: `ResPoolFileType`
		'''
		
		model = self._get_file_model(id)
		
		if model:
			path = self._get_file_path(id)
			f = ResPoolFileType(path, 'rb')
			f.hash = model.hash
			f.filename = path
			return f
	
	def get_filename(self, id):
		'''Get the filename given the ID
		
		:warning:
			Do not write to the file!
		
		:rtype: `ResPoolFilenameType`
		'''
		
		model = self._get_file_model(id)
		
		if model:
			path = self._get_file_path(id)
			s = ResPoolFilenameType(path)
			s.hash = model.hash
			return s
		
	def set_text(self, text, create=True):
		'''Store the text
		
		:parameters:
			create : `bool`
				If `False`, return `None` if text is not in database
		
		:rtype: `int`
		'''
		
		db = database.Database(self.context)
		
		sha256_obj = hashlib.sha256(text.encode('utf8'))
		digest = sha256_obj.digest()
		
		query = db.session.query(db.models.ResPoolText)
		query = query.filter_by(hash=digest)
		model = query.first()
		
		if model:
			return model.id
		
		if create:
			model = db.models.ResPoolText(
				hash=digest,
				text=text
			)
			
			db.session.add(model)
			db.session.flush()
			
			return model.id
	
	def set_file(self, fileobj, create=True):
		'''Store the file or file-like object
		
		:parameters:
			create : `bool`
				If `False`, return `None` if file is not in database
		
		:fixme: Current implementation assumes the file supports the
			seek operation
		
		:rtype: `int`
		'''
		
		# FIXME: don't rely on seek operation
		
		db = database.Database(self.context)
		
		sha256_obj = hashlib.sha256()
		
		while True:
			s = fileobj.read(2**12)
			
			if s == '':
				break
			
			sha256_obj.update(s)
		
		fileobj.seek(0)
		
		digest = sha256_obj.digest()
		
		query = db.session.query(db.models.ResPoolFile)
		query = query.filter_by(hash=digest)
		model = query.first()
		
		if model:
			return model.id
		
		if create:
			model = db.models.ResPoolFile(
				hash=digest,
			)
			
			db.session.add(model)
			db.session.flush()
			
			path = self._get_file_path(model.id)
		
			# Make dir if needed
			dirname = os.path.dirname(path)
			
			if not os.path.exists(dirname):
				os.mkdir(dirname)
			
			f_dest = open(path, 'wb')
			
			assert fileobj.tell() == 0
			shutil.copyfileobj(fileobj, f_dest)
			f_dest.close()
			
			return model.id


__all__ = ('ResPoolTextMeta', 'ResPoolFileMeta', 'ResPool', 'ResPoolUnicodeType', 
	'ResPoolFile', 'GlobalResPoolManager')
