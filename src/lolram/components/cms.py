# encoding=utf8

'''Content management system'''

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

import random
import os
import os.path
import shutil
import uuid
import hashlib
import datetime

from sqlalchemy import *
from sqlalchemy.orm import relationship

import base
from .. import dataobject
from .. import configloader
from .. import mylogger
logger = mylogger.get_logger()

from lolram import database
from .. import util

FILE_MAX = 32 ** 8 - 1
FILE_DIR_HASH = 997

ADD = 'A'
DEL = 'D'

class CMSTextsDef_1(database.TableDef):
	class CMSText(database.TableDef.get_base()):
		__tablename__ = 'cms_texts'
		
		id = Column(Integer, primary_key=True)
		text = Column(UnicodeText)
	
	desc = 'new table'
	model = CMSText
	
	def upgrade(self, engine, session):
		self.CMSText.__table__.create(engine)
	
	def downgrade(self, engine, session):
		self.CMSText.__table__.drop(engine)

class CMSTextsMeta(database.TableMeta):
	uuid = 'urn:uuid:36733eda-9239-426b-a63f-4f3d283595eb'
	
	def init(self):
		self.push(CMSTextsDef_1)

class CMSTextReferencesDef_1(database.TableDef):
	class CMSTextReference(database.TableDef.get_base()):
		__tablename__ = 'cms_text_references'
		
		id = Column(ForeignKey(CMSTextsDef_1.CMSText.id), primary_key=True)
		text = relationship(CMSTextsDef_1.CMSText)
		hash256 = Column(LargeBinary(length=32), unique=True, index=True,
			nullable=False)
	
	desc = 'new table'
	model = CMSTextReference
	
	def upgrade(self, engine, session):
		self.model.__table__.create(engine)
	
	def downgrade(self, engine, session):
		self.model.__table__.drop(engine)


class CMSTextReferencesMeta(database.TableMeta):
	uuid = 'urn:uuid:4569aea8-bb78-4dc7-9b27-e8f77630121d'
	
	def init(self):
		self.push(CMSTextReferencesDef_1)


class CMSUploadsDef_1(database.TableDef):
	class CMSUpload(database.TableDef.get_base()):
		__tablename__ = 'cms_uploads'
		
		id = Column(Integer, primary_key=True)
		filename = Column(Unicode)
	
	desc = 'new table'
	model = CMSUpload
	
	def upgrade(self, engine, session):
		self.model.__table__.create(engine)
	
	def downgrade(self, engine, session):
		self.model.__table__.drop(engine)

class CMSUploadsMeta(database.TableMeta):
	uuid = 'urn:uuid:01cd9f70-d164-4dda-a67e-7be823704dd0'
	
	def init(self):
		self.push(CMSUploadsDef_1)


class CMSUploadReferencesDef_1(database.TableDef):
	class CMSUploadReference(database.TableDef.get_base()):
		__tablename__ = 'cms_upload_references'
		
		id = Column(ForeignKey(CMSUploadsDef_1.CMSUpload.id), primary_key=True)
		upload = relationship(CMSUploadsDef_1.CMSUpload)
		sha256 = Column(LargeBinary(length=32), nullable=False, index=True,
			unique=True)
	
	desc = 'new table'
	model = CMSUploadReference
	
	def upgrade(self, engine, session):
		self.model.__table__.create(engine)
	
	def downgrade(self, engine, session):
		self.model.__table__.drop(engine)


class CMSUploadReferencesMeta(database.TableMeta):
	uuid = 'urn:uuid:ab9304fb-f276-4dcc-95f9-0c781e1f2829'
	
	def init(self):
		self.push(CMSUploadReferencesDef_1)


class CMSArticlesDef_1(database.TableDef):
	class CMSArticle(database.TableDef.get_base()):
		__tablename__ = 'cms_articles'
		
		id = Column(Integer, primary_key=True)
		text_id = Column(ForeignKey(CMSTextsDef_1.CMSText.id))
		text = relationship(CMSTextsDef_1.CMSText)
		upload_id = Column(ForeignKey(CMSUploadsDef_1.CMSUpload.id))
		upload = relationship(CMSUploadsDef_1.CMSUpload)
		date = Column(DateTime, default=datetime.datetime.utcnow)
		title = Column(Unicode)
		uuid = Column(LargeBinary(length=16), default=lambda:uuid.uuid4().bytes)
	
	desc = 'new table'
	model = CMSArticle
	
	def upgrade(self, engine, session):
		self.CMSArticle.__table__.create(engine)
	
	def downgrade(self, engine, session):
		self.CMSArticle.__table__.drop(engine)

class CMSArticlesMeta(database.TableMeta):
	uuid = 'urn:uuid:f9d34d49-5226-48a1-a115-3c07de711071'
	
	def init(self):
		self.push(CMSArticlesDef_1)


class CMSAddressesDef_1(database.TableDef):
	class CMSAddress(database.TableDef.get_base()):
		__tablename__ = 'cms_addresses'
		
		id = Column(Integer, primary_key=True)
		name = Column(Unicode, nullable=False, unique=True, index=True)
		article_id = Column(ForeignKey(CMSArticlesDef_1.CMSArticle.id),
			nullable=False)
		article = relationship(CMSArticlesDef_1.CMSArticle)
	
	desc = 'new table'
	model = CMSAddress
	
	def upgrade(self, engine, session):
		self.model.__table__.create(engine)
	
	def downgrade(self, engine, session):
		self.model.__table__.drop(engine)


class CMSAddressesMeta(database.TableMeta):
	uuid = 'urn:uuid:02e2bb62-81c2-4b50-8417-e26d3011da61'
	
	def init(self):
		self.push(CMSAddressesDef_1)


class CMSAddressHistoryDef_1(database.TableDef):
	class CMSAddressHistory(database.TableDef.get_base()):
		__tablename__ = 'cms_address_history'
		
		id = Column(Integer, primary_key=True)
		action = Column(Enum(ADD, DEL), nullable=False)
		name = Column(Unicode, nullable=False,)
		article_id = Column(ForeignKey(CMSArticlesDef_1.CMSArticle.id), 
			nullable=False)
		article = relationship(CMSArticlesDef_1.CMSArticle)
		created = Column(DateTime, default=datetime.datetime.utcnow)
	
	desc = 'new table'
	model = CMSAddressHistory
	
	def upgrade(self, engine, session):
		self.model.__table__.create(engine)
	
	def downgrade(self, engine, session):
		self.model.__table__.drop(engine)


class CMSAddressHistoryMeta(database.TableMeta):
	uuid = 'urn:uuid:1fc5c229-f387-4a29-9def-5f583ea03c57'
	
	def init(self):
		self.push(CMSAddressHistoryDef_1)


class CMSHistoryDef_1(database.TableDef):
	class CMSHistory(database.TableDef.get_base()):
		__tablename__ = 'cms_history'
		
		id = Column(Integer, primary_key=True)
		article_id = Column(ForeignKey(CMSArticlesDef_1.CMSArticle.id),
			index=True)
		article = relationship(CMSArticlesDef_1.CMSArticle)
		text_id = Column(ForeignKey(CMSTextsDef_1.CMSText.id))
		text = relationship(CMSTextsDef_1.CMSText)
		upload_id = Column(ForeignKey(CMSUploadsDef_1.CMSUpload.id))
		upload = relationship(CMSUploadsDef_1.CMSUpload)
		reason = Column(Unicode)
		upload_filename = Column(Unicode)
		created = Column(DateTime, default=datetime.datetime.utcnow)
	
	desc = 'new table'
	model = CMSHistory
	
	def upgrade(self, engine, session):
		self.model.__table__.create(engine)
	
	def downgrade(self, engine, session):
		self.model.__table__.drop(engine)


class CMSHistoryMeta(database.TableMeta):
	uuid = 'urn:uuid:597f9776-3e38-4c91-87fd-295f1b8ab29d'
	
	def init(self):
		self.push(CMSHistoryDef_1)


class CMSArticleTreeDef_1(database.TableDef):
	class CMSArticleTree(database.TableDef.get_base()):
		__tablename__ = 'cms_article_tree'
		
		id = Column(Integer, primary_key=True)
		article_id = Column(ForeignKey(CMSArticlesDef_1.CMSArticle.id), 
			nullable=False)
		article = relationship(CMSArticlesDef_1.CMSArticle,
			primaryjoin=article_id==CMSArticlesDef_1.CMSArticle.id)
		child_id = Column(ForeignKey(CMSArticlesDef_1.CMSArticle.id), 
			nullable=False)
		child = relationship(CMSArticlesDef_1.CMSArticle,
			primaryjoin=child_id==CMSArticlesDef_1.CMSArticle.id)

	desc = 'new table'
	model = CMSArticleTree
	
	def upgrade(self, engine, session):
		self.model.__table__.create(engine)
	
	def downgrade(self, engine, session):
		self.model.__table__.drop(engine)


class CMSArticleTreeMeta(database.TableMeta):
	uuid = 'urn:uuid:b4227b69-c4ce-47e6-910a-e5b9f7c1f8df'
	
	def init(self):
		self.push(CMSArticleTreeDef_1)


class CMSArticleTreeHistoryDef_1(database.TableDef):
	class CMSArticleTreeHistory(database.TableDef.get_base()):
		__tablename__ = 'cms_article_tree_history'
		
		id = Column(Integer, primary_key=True)
		article_id = Column(ForeignKey(CMSArticlesDef_1.CMSArticle.id), 
			nullable=False)
		article = relationship(CMSArticlesDef_1.CMSArticle,
			primaryjoin=article_id==CMSArticlesDef_1.CMSArticle.id)
		child_id = Column(ForeignKey(CMSArticlesDef_1.CMSArticle.id), 
			nullable=False)
		child = relationship(CMSArticlesDef_1.CMSArticle,
			primaryjoin=child_id==CMSArticlesDef_1.CMSArticle.id)
		reason = Column(Unicode)
		created = Column(DateTime, default=datetime.datetime.utcnow)
		action = Column(Enum(ADD, DEL), nullable=False)

	desc = 'new table'
	model = CMSArticleTreeHistory
	
	def upgrade(self, engine, session):
		self.model.__table__.create(engine)
	
	def downgrade(self, engine, session):
		self.model.__table__.drop(engine)

class CMSArticleTreeHistoryMeta(database.TableMeta):
	uuid = 'urn:uuid:0f623308-1044-4aed-bf05-f0bcf4752eb7'
	
	def init(self):
		self.push(CMSArticleTreeHistoryDef_1)

class Article(object):
	def __init__(self, fardel=None, model=None, agent=None):
		self._id = None
		self._text = None
		self._file = None
		self._model = model
		self._fardel = fardel
		self._agent = agent
		self._uuid = None
	
	@property
	def id(self):
		return self._id
	
	@property
	def uuid(self):
		return self._uuid
	
	@property
	def text(self):
		return self._text
	
	@text.setter
	def text(self, t):
		pass
		#TODO
	
	@property
	def file(self):
		return self._file
	
	@file.setter
	def file(self, file_obj):
		pass
		#TODO
	
	@property
	def title(self):
		return self._title
	
	@title.setter
	def title(self, s):
		pass
		#TODO
	
	@property
	def date(self):
		return self._date
	
	@date.setter
	def date(self, d):
		pass
		#TODO
	
	def get_history(self, start=0, end=None):
		query = self._fardel.database.session.query(
			self._fardel.database.models.CMSHistory) \
			.filter_by(article_id=self._id) \
			.order_by(self._fardel.database.models.CMSHistory.created) \
			.slice(start, end)
		
		i = start
		for model in query:
			yield dataobject.DataObject(dict(revision=i,
				reason=model.reason,
				file_id=model.upload_id,
				text_id=model.text_id,
				filename=model.upload_filename,
				date=model.created,
				version=i
			) )
			
			i += 1
		
	def get_addresses(self):
		query = self._fardel.database.session.query(
			self._fardel.database.models.CMSAddress) \
			.filter_by(article_id=self._id)
		
		for model in query:
			yield model.name
	
	def get_parents(self):
		query = self._fardel.database.session.query(
			self._fardel.database.models.CMSArticleTree) \
			.filter_by(child_id=self._id)
		
		for model in query:
			yield model.article_id
	
	def get_children(self):
		query = self._fardel.database.session.query(
			self._fardel.database.models.CMSArticleTree) \
			.filter_by(article_id=self._id)
		
		for model in query:
			yield model.child_id

class CMSAgent(base.BaseComponentAgent):
	def __init__(self, fardel, manager):
		self._fardel = fardel
		self._manager = manager
	
	def get_text_model(self, id):
		query = self._fardel.database.session.query(
			self._fardel.database.models.CMSText)
		query = query.filter_by(id=id)
		model = query.first()
		
		return model
		
	def get_text(self, id):
		model = self.get_text_model(id)
		
		return model.text if model else None
	
	def set_text(self, id, text):
		if id is not None:
			model = self.get_text_model(id)
		else:
			model = self._fardel.database.models.CMSText()
			self._fardel.database.session.add(model)
		
		model.text = text
		
		self._fardel.database.session.flush()
		return model.id
	
	def get_pooled_text_id(self, text, create=False):
		sha256_obj = hashlib.sha256(text)
		digest = sha256_obj.digest()
		
		query = self._fardel.database.session.query(
			self._fardel.database.models.CMSTextReference)
		query = query.filter_by(hash256=digest)
		
		result = query.first()
		
		if result:
			return result.text.id
		elif create:
			ref_model = self._fardel.database.models.CMSTextReference()
			ref_model.hash256 = digest
			ref_model.id = self.set_text(None, text)
			
			self._fardel.database.session.add(ref_model)
			
			return ref_model.id
	
	def get_file_path(self, id):
		hash_val = str(id % FILE_DIR_HASH)
		filename = util.bytes_to_b32low(util.int_to_bytes(id))
		path = os.path.join(self._fardel.dirs.upload, hash_val, filename)
		return path
	
	def get_file(self, id):
		path = self.get_file_path(id)
		
		if os.path.exists(path):
			return open(path, 'rb')
	
	def add_file(self, file_obj, filename=None):
#		while True:
#			id = random.randint(0, FILE_MAX)
#			path = self._get_file_path(id)	
#			if not os.path.exists(path):
#				break
		model = self._fardel.database.models.CMSUpload()
		model.filename = filename
		self._fardel.database.session.add(model)
		self._fardel.database.session.flush()
		
		id = model.id
		path = self.get_file_path(id)
		
		# Make dir if needed
		dirname = os.path.dirname(path)
		
		if not os.path.exists(dirname):
			os.mkdir(dirname)
		
		f_dest = open(path, 'wb')
		
		shutil.copyfileobj(file_obj, f_dest)
		f_dest.close()
		
		return id
	
	def get_pooled_file_id(self, file_obj, create=False):
		sha256_obj = hashlib.sha256()
		
		while True:
			v = file_obj.read(2**12)
			
			if v == '':
				break
			
			sha256_obj.update(v)
		
		digest = sha256_obj.digest()
		
		query = self._fardel.database.session.query(
			self._fardel.database.models.CMSUploadReference)
		query = query.filter_by(sha256=digest)
		
		result = query.first()
		
		if result:
			return result.id
		elif create:
			ref_model = self._fardel.database.models.CMSUploadReference()
			ref_model.sha256 = digest
			file_obj.seek(0)
			ref_model.id = self.add_file(file_obj)
			
			self._fardel.database.session.add(ref_model)
			
			return ref_model.id
	
	def get_article_model(self, id):
		query = self._fardel.database.session.query(
			self._fardel.database.models.CMSArticle)
		query = query.filter_by(id=id)
		
		return query.first()
	
	def get_article(self, id):
		model = self.get_article_model(id)	
		
		if model:
			article = Article(self._fardel, model)
			article._id = model.id
			article._title = model.title
			article._date = model.date
			article._uuid = model.uuid
			
			if model.text:
				article._text = model.text.text
			
			if model.upload:
				article._file = self.get_file(model.upload.id)
			
			return article
	
	def save_article(self, id, text=None, file_obj=None, filename=None, 
	date=None, title=None, reason=None):
		if id is not None:
			model = self.get_article_model(id)
		else:
			model = self._fardel.database.models.CMSArticle()
			self._fardel.database.session.add(model)
		
		model.title = title
		
		history_model = self._fardel.database.models.CMSHistory()
		
		self._fardel.database.session.add(history_model)
		
		history_model.article = model
		history_model.reason = reason
		
		if date:
			model.date = date
		
		if text is not None:
			model.text_id = self.get_pooled_text_id(text, create=True)
			history_model.text_id = model.text_id
		
		if file_obj:
			model.upload_id = self.get_pooled_file_id(file_obj, create=True)
			history_model.upload_id = model.upload_id
			history_model.upload_filename = filename
		
		self._fardel.database.session.flush()
		return model.id
	
	def get_address_model(self, address):
		query = self._fardel.database.session.query(
			self._fardel.database.models.CMSAddress) \
			.filter_by(name=address)
		
		return query.first()
	
	def get_address(self, address):
		model = self.get_address_model(address)
		
		if model:
			return model.article_id
	
	def set_address(self, address, article_id):
		model = self.get_address_model(address)
		
		if not model:
			model = self._fardel.database.models.CMSAddress()
			model.name = address
			self._fardel.database.session.add(model)
			
			history_model = self._fardel.database.models.CMSAddressHistory()
			self._fardel.database.session.add(history_model)
			history_model.action = ADD
			history_model.name = address
			history_model.article_id = article_id
			
		
		model.article_id = article_id
	
	def delete_address(self, address):
		model = self.get_address_model(address)
		
		if model:
			history_model = self._fardel.database.models.CMSAddressHistory()
			self._fardel.database.session.add(history_model)
			history_model.action = DEL
			history_model.name = address
			history_model.article_id = model.article_id
			
			self._fardel.database.session.delete(model)
	
	def add_child(self, article_id, child_id, reason=None):
		CMSArticleTree = self._fardel.database.models.CMSArticleTree
		query = self._fardel.database.session.query(CMSArticleTree) \
			.filter_by(article_id=article_id) \
			.filter_by(child_id=child_id)
		
		if not query.first():
			model = self._fardel.database.models.CMSArticleTree()
			history_model = self._fardel.database.models.CMSArticleTreeHistory()
			model.article_id = article_id
			model.child_id = child_id
			history_model.article_id = article_id
			history_model.child_id = child_id
			history_model.action = ADD
			history_model.reason = reason
			self._fardel.database.session.add(model)
			self._fardel.database.session.add(history_model)
	
	def remove_child(self, article_id, child_id, reason=None):
		CMSArticleTree = self._fardel.database.models.CMSArticleTree
		query = self._fardel.database.session.query(CMSArticleTree) \
			.filter_by(article_id=article_id) \
			.filter_by(child_id=child_id)
		
		model = query.first()
		
		if model:
			history_model = self._fardel.database.models.CMSArticleTreeHistory()
			self._fardel.database.session.add(history_model)
			history_model.article_id = model.article_id
			history_model.child_id = model.child_id
			history_model.action = DEL
			history_model.reason = reason
			
		query.delete()

class CMSManager(base.BaseComponentManager):
	default_config = configloader.DefaultSectionConfig('cms',
		perm_cookie_name='lolramsid',
	)
	name = 'cms'
	agent_class = CMSAgent

	def __init__(self, fardel):
		fardel.component_managers.database.add(CMSTextsMeta())
		fardel.component_managers.database.add(CMSTextReferencesMeta())
		fardel.component_managers.database.add(CMSUploadsMeta())
		fardel.component_managers.database.add(CMSUploadReferencesMeta())
		fardel.component_managers.database.add(CMSArticlesMeta())
		fardel.component_managers.database.add(CMSAddressesMeta())
		fardel.component_managers.database.add(CMSHistoryMeta())
		fardel.component_managers.database.add(CMSAddressHistoryMeta())
		fardel.component_managers.database.add(CMSArticleTreeMeta())
		fardel.component_managers.database.add(CMSArticleTreeHistoryMeta())
