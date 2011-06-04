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
import json

from sqlalchemy import *
from sqlalchemy.orm import relationship
import sqlalchemy.sql

import base
import database
from .. import dataobject
from .. import configloader
from .. import iso8601

from .. import util

FILE_MAX = 32 ** 8 - 1
FILE_DIR_HASH = 997

ADD = 'A'
DEL = 'D'

class CMSTextsMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSText(database.TableMeta.Def.base()):
			__tablename__ = 'cms_texts'
			
			id = Column(Integer, primary_key=True)
			text = Column(UnicodeText)
		
		desc = 'new table'
		model = CMSText
		
		def upgrade(self, engine, session):
			self.CMSText.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.CMSText.__table__.drop(engine)

	uuid = 'urn:uuid:36733eda-9239-426b-a63f-4f3d283595eb'
	
	defs = (D1,)

class CMSTextReferencesMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSTextReference(database.TableMeta.Def.base()):
			__tablename__ = 'cms_text_references'
			
			id = Column(ForeignKey(CMSTextsMeta.D1.CMSText.id), primary_key=True)
			text = relationship(CMSTextsMeta.D1.CMSText)
			hash256 = Column(LargeBinary(length=32), unique=True, index=True,
				nullable=False)
		
		desc = 'new table'
		model = CMSTextReference
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)

	uuid = 'urn:uuid:4569aea8-bb78-4dc7-9b27-e8f77630121d'
	defs = (D1, )


class CMSUploadsMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSUpload(database.TableMeta.Def.base()):
			__tablename__ = 'cms_uploads'
			
			id = Column(Integer, primary_key=True)
			filename = Column(Unicode)
		
		desc = 'new table'
		model = CMSUpload
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)

	uuid = 'urn:uuid:01cd9f70-d164-4dda-a67e-7be823704dd0'
	defs = (D1, )


class CMSUploadReferencesMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSUploadReference(database.TableMeta.Def.base()):
			__tablename__ = 'cms_upload_references'
			
			id = Column(ForeignKey(CMSUploadsMeta.D1.CMSUpload.id), primary_key=True)
			upload = relationship(CMSUploadsMeta.D1.CMSUpload)
			sha256 = Column(LargeBinary(length=32), nullable=False, index=True,
				unique=True)
			fileinfo = Column(Unicode)
			mimetype = Column(Unicode) 
		
		desc = 'new table'
		model = CMSUploadReference
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)

	uuid = 'urn:uuid:ab9304fb-f276-4dcc-95f9-0c781e1f2829'
	defs = (D1, )


class CMSArticlesMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSArticle(database.TableMeta.Def.base()):
			__tablename__ = 'cms_articles'
			
			id = Column(Integer, primary_key=True)
			text_id = Column(ForeignKey(CMSTextsMeta.D1.CMSText.id))
			text = relationship(CMSTextsMeta.D1.CMSText)
			upload_id = Column(ForeignKey(CMSUploadsMeta.D1.CMSUpload.id))
			upload = relationship(CMSUploadsMeta.D1.CMSUpload)
			date = Column(DateTime, default=datetime.datetime.utcnow)
			title = Column(Unicode)
			uuid = Column(LargeBinary(length=16), default=lambda:uuid.uuid4().bytes, index=True)
		
		desc = 'new table'
		model = CMSArticle
		
		def upgrade(self, engine, session):
			self.CMSArticle.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.CMSArticle.__table__.drop(engine)

	uuid = 'urn:uuid:f9d34d49-5226-48a1-a115-3c07de711071'
	defs = (D1, )


class CMSAddressesMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSAddress(database.TableMeta.Def.base()):
			__tablename__ = 'cms_addresses'
			
			id = Column(Integer, primary_key=True)
			name = Column(Unicode, nullable=False, unique=True, index=True)
			article_id = Column(ForeignKey(CMSArticlesMeta.D1.CMSArticle.id),
				nullable=False)
			article = relationship(CMSArticlesMeta.D1.CMSArticle)
		
		desc = 'new table'
		model = CMSAddress
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)

	uuid = 'urn:uuid:02e2bb62-81c2-4b50-8417-e26d3011da61'
	defs = (D1,)

#class CMSAddressHistoryMeta(database.TableMeta):
#	class D1(database.TableMeta.Def):
#		class CMSAddressHistory(database.TableMeta.Def.base()):
#			__tablename__ = 'cms_address_history'
#			
#			id = Column(Integer, primary_key=True)
#			action = Column(Enum(ADD, DEL), nullable=False)
#			name = Column(Unicode, nullable=False,)
#			article_id = Column(ForeignKey(CMSArticlesMeta.D1.CMSArticle.id), 
#				nullable=False)
#			article = relationship(CMSArticlesMeta.D1.CMSArticle)
#			created = Column(DateTime, default=datetime.datetime.utcnow)
#		
#		desc = 'new table'
#		model = CMSAddressHistory
#		
#		def upgrade(self, engine, session):
#			self.model.__table__.create(engine)
#		
#		def downgrade(self, engine, session):
#			self.model.__table__.drop(engine)
#
#
#	uuid = 'urn:uuid:1fc5c229-f387-4a29-9def-5f583ea03c57'
#	defs = (D1,)


class CMSHistoryMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSHistory(database.TableMeta.Def.base()):
			__tablename__ = 'cms_history'
			
			id = Column(Integer, primary_key=True)
			article_id = Column(ForeignKey(CMSArticlesMeta.D1.CMSArticle.id),
				index=True)
			article = relationship(CMSArticlesMeta.D1.CMSArticle)
			text_id = Column(ForeignKey(CMSTextsMeta.D1.CMSText.id))
			text = relationship(CMSTextsMeta.D1.CMSText)
			upload_id = Column(ForeignKey(CMSUploadsMeta.D1.CMSUpload.id))
			upload = relationship(CMSUploadsMeta.D1.CMSUpload)
			reason = Column(Unicode)
			upload_filename = Column(Unicode)
			created = Column(DateTime, default=datetime.datetime.utcnow)
			uuid = Column(LargeBinary(length=16), default=lambda:uuid.uuid4().bytes, index=True)
		
		desc = 'new table'
		model = CMSHistory
	
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)

	uuid = 'urn:uuid:597f9776-3e38-4c91-87fd-295f1b8ab29d'
	defs = (D1,)


class CMSArticleTreeMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSArticleTree(database.TableMeta.Def.base()):
			__tablename__ = 'cms_article_tree'
			
			id = Column(Integer, primary_key=True)
			article_id = Column(ForeignKey(CMSArticlesMeta.D1.CMSArticle.id), 
				nullable=False)
			article = relationship(CMSArticlesMeta.D1.CMSArticle,
				primaryjoin=article_id==CMSArticlesMeta.D1.CMSArticle.id)
			child_id = Column(ForeignKey(CMSArticlesMeta.D1.CMSArticle.id), 
				nullable=False)
			child = relationship(CMSArticlesMeta.D1.CMSArticle,
				primaryjoin=child_id==CMSArticlesMeta.D1.CMSArticle.id)
	
		desc = 'new table'
		model = CMSArticleTree
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)

	uuid = 'urn:uuid:b4227b69-c4ce-47e6-910a-e5b9f7c1f8df'
	defs = (D1,)

#class CMSArticleTreeHistoryMeta(database.TableMeta):
#	class D1(database.TableMeta.Def):
#		class CMSArticleTreeHistory(database.TableMeta.Def.base()):
#			__tablename__ = 'cms_article_tree_history'
#			
#			id = Column(Integer, primary_key=True)
#			article_id = Column(ForeignKey(CMSArticlesMeta.D1.CMSArticle.id), 
#				nullable=False)
#			article = relationship(CMSArticlesMeta.D1.CMSArticle,
#				primaryjoin=article_id==CMSArticlesMeta.D1.CMSArticle.id)
#			child_id = Column(ForeignKey(CMSArticlesMeta.D1.CMSArticle.id), 
#				nullable=False)
#			child = relationship(CMSArticlesMeta.D1.CMSArticle,
#				primaryjoin=child_id==CMSArticlesMeta.D1.CMSArticle.id)
#			reason = Column(Unicode)
#			created = Column(DateTime, default=datetime.datetime.utcnow)
#			action = Column(Enum(ADD, DEL), nullable=False)
#	
#		desc = 'new table'
#		model = CMSArticleTreeHistory
#		
#		def upgrade(self, engine, session):
#			self.model.__table__.create(engine)
#		
#		def downgrade(self, engine, session):
#			self.model.__table__.drop(engine)
#
#	uuid = 'urn:uuid:0f623308-1044-4aed-bf05-f0bcf4752eb7'
#	defs = (D1, )


class CMS(base.BaseComponent):
	def init(self):
		db = self.context.get_instance(database.Database)
		db.add(CMSTextsMeta)
		db.add(CMSUploadsMeta)
		db.add(CMSTextReferencesMeta)
		db.add(CMSUploadReferencesMeta)
		db.add(CMSArticlesMeta)
		db.add(CMSArticleTreeMeta)
		db.add(CMSHistoryMeta)
		db.add(CMSAddressesMeta)
	
	def setup(self):
		self._db = self.context.get_instance(database.Database)
	
	def new_article(self):
		'''Create a new article
		
		:rtype: `Article`
		'''
		
		model = self._db.models.CMSArticle()
		self._db.session.add(model)
		return Article(self.context, self, model)
	
	def get_article(self, id=None, uuid=None, address=None):
		'''Get an article by its ID
		
		:rtype: `Article`
		'''
		
		model = None
		
		if address:
			query = self._db.session.query(self._db.models.CMSAddress)
			query = query.filter_by(name=address)
			
			address_model = query.first()
			
			if address_model:
				model = address_model.article
		
		else:
			query = self._db.session.query(self._db.models.CMSArticle)
			
			if id:
				query = query.filter_by(id=id)
			else:
				query = query.filter_by(uuid=uuid)
		
			model = query.first()
			
		if model:
			return Article(self.context, self, model)
	
	def get_article_history(self, id=None, uuid=None):
		'''Get a single article history by ID
		
		:rtype: `ArticleHistory`
		'''
		
		query = self._db.session.query(self._db.models.CMSHistory)
		
		if id:
			query = query.filter_by(id=id)
		else:
			query = query.filter_by(uuid=uuid)
	
		model = query.first()
		
		if model:
			return ArticleHistory(self.context, self, model) 
	
	def get_articles(self, offset=0, limit=51, date_sort_desc=False):
		'''Get a list of articles
		
		:rtype: `list`
		:returns: a `list` of `Article`
		'''
		
		query = self._db.session.query(self._db.models.CMSArticle)
		
		if date_sort_desc:
			query = query.order_by(
				sqlalchemy.sql.desc(self._db.models.CMSArticle.date))
		else:
			query = query.order_by(self._db.models.CMSArticle.date)
		
		l = []
		
		for model in query[offset:offset+limit]:
			l.append(Article(self.context, self, model))
		
		return l
	
	def get_histories(self, offset, limit=51, date_sort_desc=False,
	article_id=None, article_uuid=None):
		'''Get a list of article histories
		
		:rtype: `list`
		:returns: a `list` of `ArticleHistory`
		'''
		
		query = self._db.session.query(self._db.models.CMSHistory)
		
		if article_uuid:
			article = self.get_article(uuid=article_uuid)
			
			if article:
				article_id = article.id
		
		if article_id:
			query = query.filter_by(article_id=article_id)
		
		if date_sort_desc:
			query = query.order_by(
				sqlalchemy.sql.desc(self._db.models.CMSHistory.created))
		else:
			query = query.order_by(self._db.models.CMSHistory.created)
		
		l = []
		i = 0
		
		for model in query[offset:offset+limit]:
			ah = ArticleHistory(self.context, self, model)
			ah._number = i
			l.append(ah)
			
			i += 1
		
		return l
	
	def _get_db(self):
		return self.context.get_instance(database.Database)
	
	def _get_text_model(self, id):
		db = self._get_db()
		query = db.session.query(db.models.CMSText)
		query = query.filter_by(id=id)
		model = query.first()
		
		return model
	
	def _get_text(self, id):
		model = self._get_text_model(id)
		
		return model.text if model else None
	
	def _set_text(self, id, text):
		if id is not None:
			model = self._get_text_model(id)
		else:
			db = self._get_db()
			model = db.models.CMSText()
			db.session.add(model)
			db.session.flush()
		
		model.text = text
		
		return model.id
	
	def _get_pooled_text_id(self, text, create=False):
		sha256_obj = hashlib.sha256(text)
		digest = sha256_obj.digest()
		
		db = self._get_db()
		
		query = db.session.query(db.models.CMSTextReference)
		query = query.filter_by(hash256=digest)
		result = query.first()
		
		if result:
			return result.text.id
		elif create:
			ref_model = db.models.CMSTextReference()
			ref_model.hash256 = digest
			ref_model.id = self._set_text(None, text)
			
			db.session.add(ref_model)
			
			return ref_model.id
	
	def _get_file_path(self, id):
		hash_val = str(id % FILE_DIR_HASH)
		filename = util.bytes_to_b32low(util.int_to_bytes(id))
		path = os.path.join(self.context.dirinfo.upload, hash_val, filename)
		return path
	
	def _get_file(self, id):
		path = self._get_file_path(id)
		
		if os.path.exists(path):
			return open(path, 'rb')
	
	def _add_file(self, file_obj, filename=None):
#		while True:
#			id = random.randint(0, FILE_MAX)
#			path = self._get_file_path(id)	
#			if not os.path.exists(path):
#				break
		db = self._get_db()
		model = db.models.CMSUpload()
		model.filename = filename
		db.session.add(model)
		db.session.flush()
		
		id = model.id
		path = self._get_file_path(id)
		
		# Make dir if needed
		dirname = os.path.dirname(path)
		
		if not os.path.exists(dirname):
			os.mkdir(dirname)
		
		f_dest = open(path, 'wb')
		
		shutil.copyfileobj(file_obj, f_dest)
		f_dest.close()
		
		return id
	
	def _get_pooled_file_id(self, file_obj, create=False):
		sha256_obj = hashlib.sha256()
		
		while True:
			v = file_obj.read(2**12)
			
			if v == '':
				break
			
			sha256_obj.update(v)
		
		digest = sha256_obj.digest()
		
		db = self._get_db()
		query = db.session.query(db.models.CMSUploadReference)
		query = query.filter_by(sha256=digest)
		result = query.first()
		
		if result:
			return result.id
		elif create:
			ref_model = db.models.CMSUploadReference()
			ref_model.sha256 = digest
			file_obj.seek(0)
			ref_model.id = self._add_file(file_obj)
			
			db.session.add(ref_model)
			
			return ref_model.id

class _ArticleView(dataobject.ProtectedObject):
	TEXT = 'text'
	PARENTS = 'parents'
	ADDRESSES = 'addresses'
	DATE = 'date'
	TITLE = 'title'
	
	def __init__(self, context, cms, model):
		self._context = context
		self._cms = cms
		self._model = model
		self._db = context.get_instance(database.Database)
		self._text = None
		self._file = None
		self._metadata = None
		self._dirty_articles = set()
	
	def __hash__(self):
		return self._model.__hash__()
	
	def __cmp__(self, other):
		return self._model == other
	
	@property
	def id(self):
		'''Get the database ID'''
		
		return self._model.id
	
	@property
	def uuid(self):
		'''Get the UUID for this article
		
		The UUID encompasses the history set of this article
		
		:rtype: `bytes`
		'''
		
		return self._model.uuid
	
	@property
	def metadata(self):
		'''Get the metadata
		
		:rtype: `dict`
		'''
		
		if self._metadata is None:
			self._metadata = json.loads(self.raw_text or '{}')
			
		return self._metadata
	
	@property
	def raw_text(self):
		'''Get the raw text
		
		:rtype: `unicode`
		'''
		
		if self._text:
			return self._text
		
		if self._model.text:
			return self._model.text.text
	
	@property
	def text(self):
		'''Get the article text
		
		:rtype: `unicode`
		'''
		
		return self.metadata.get('text')

	@property
	def filename(self):
		'''Get the disk filename of this file
		
		:rtype: `unicode`
		'''
		
		if self._model.upload:
			return self._cms._get_file_path(self._model.upload.id)
	
	@property
	def file(self):
		'''Get a read-only `file` instance to the file
		
		:rtype: `file`
		'''
		
		filename = self.filename
		
		if filename:
			return open(filename, 'rb')
	
	@property
	def addresses(self):
		'''Get a list of addresses for this article
		
		:rtype: `list`
		'''
		
		return frozenset(self.metadata.get(self.ADDRESSES, []))
	
	@property
	def parents(self):
		'''Get parent articles for this article
		
		:rtype: `set`
		'''
		
		parents = self.metadata.get(self.PARENTS, [])
		
		l = set()
		for parent_uuid in parents:
			parent_uuid = parent_uuid.decode('hex')
			l.add(self._cms.get_article(uuid=parent_uuid))
		
		return frozenset(l)
	
	@property
	def children(self):
		'''Get child articles for this article
		
		:rtype: `set`
		'''
		
		query = self._db.session.query(self._db.models.CMSArticleTree)
		query = query.filter_by(article_id=self._model.id)
		
		l = set()
		for model in query:
			article = Article(self._context, self._cms, model.child)
			l.add(article)
		
		return frozenset(l)
	
class ArticleHistory(_ArticleView):
	@property
	def number(self):
		return self._number
	
	@property
	def upload_filename(self):
		'''Get the originally uploaded filename'''
		
		if self._model.file:
			return self._model.upload_filename
	
	@property
	def created(self):
		'''Get when the article was edited
		
		:rtype: `datetime.Datetime`
		'''
		return self._model.created

class Article(_ArticleView):
	@property
	def date(self):
		'''Get the most recent version of the published date
		
		:see:
			See `ArticleHistory.created` for info on how to get the date
			in which the article was edited.
		
		:rtype: `datetime.Datetime`
		'''
		return self._model.date
	
	@property
	def title(self):
		'''Get the most recent version of the published title
		
		:see:
			See `Article.get_metadata` or `ArticleHistory.get_metadata`
			to retrieve other possible metadata
		
		:rtype:`unicode`
		'''
		
		return self._model.title
	
	@_ArticleView.parents.setter
	def parents(self, parent_articles):
		
		if parent_articles:
			parent_article_uuids = []
			for article in iter(frozenset(parent_articles)):
				parent_article_uuids.append(article.uuid.encode('hex'))
			
			self.metadata[self.PARENTS] = parent_article_uuids
		
		elif self.PARENTS in self.metadata:
			del self.metadata[self.PARENTS]
	
#	@_ArticleView.children.setter
#	def children(self, child_articles):
#		for child in child_articles:
#			child.parents = child.parents | frozenset((self,))
#			self._dirty_articles.add(child)
	
	@_ArticleView.addresses.setter
	def addresses(self, addresses):
		if addresses:
			self.metadata[self.ADDRESSES] = list(frozenset(addresses))
		elif self.ADDRESSES in self.metadata:
			del self.metadata[self.ADDRESSES]
		
	def set_file(self, file_obj=None, path=None, upload_filename=None):
		self._file = (file_obj, path, upload_filename)
	
	@_ArticleView.text.setter
	def text(self, t):
		assert isinstance(t, unicode)
		self.metadata[self.TEXT] = t
	
	@_ArticleView.raw_text.setter
	def raw_text(self, t):
		assert isinstance(t, unicode)
		self._text = t
	
	def save(self, reason=None):
		history_model = self._db.models.CMSHistory()
		model = self._model
		self._db.session.add(history_model)
		
		if self.DATE in self.metadata:
			o = self.metadata[self.DATE]
			
			if isinstance(o, datetime.datetime):
				date_datetime = o
				date_str = str(o)
			else:
				date_str = o
				date_datetime = iso8601.parse_date(o)
			
			model.date = date_datetime
			self.metadata[self.DATE] = date_str
		
		model.title = self.metadata.get('title')
			
		if self._text:
			model.text_id = self._cms._get_pooled_text_id(self._text, create=True)
		elif self._metadata:
			model.text_id = self._cms._get_pooled_text_id(json.dumps(self._metadata), create=True)
		
		if self._file:
			file_obj, path, upload_filename = self._file
			model.upload_id = self._cms._get_pooled_file_id(file_obj or open(path, 'rb'), create=True)
			history_model.upload_filename = upload_filename
		
		query = self._db.session.query(self._db.models.CMSAddress)
		query = query.filter_by(article_id=self._model.id)
		query = query.filter(~self._db.models.CMSAddress.name.in_(self.addresses))
		query.delete(synchronize_session='fetch')
		
		for address in self.addresses:
			query = self._db.session.query(self._db.models.CMSAddress)
			query = query.filter_by(name=address)
			
			model = query.first()
			
			if not model:
				model = self._db.models.CMSAddress()
				self._db.session.add(model)
				model.name = address
			
			model.article = self._model
		
		CMSArticleTree = self._db.models.CMSArticleTree
		query = self._db.session.query(self._db.models.CMSArticleTree)
		query = query.filter_by(child_id=self._model.id)
		query = query.filter(~CMSArticleTree.article_id.in_(
			map(lambda article: article._model.id, self.parents)))
		query.delete(synchronize_session='fetch')
		
		for parent in self.parents:
			query = self._db.session.query(self._db.models.CMSArticleTree)
			query = query.filter_by(article_id=parent._model.id, 
				child_id=self._model.id)
			
			model = query.first()
			
			if model:
				continue
			
			model = self._db.models.CMSArticleTree()
			self._db.session.add(model)
			model.article_id = parent._model.id
			model.child_id = self._model.id
		
		history_model.article = self._model
		history_model.reason = reason
		history_model.text_id = self._model.text_id
		history_model.upload_id = self._model.upload_id
		
		self._db.session.flush()
		
		for child in self._dirty_articles:
			child.save(reason)
		
	def get_history(self, offset, limit=51, date_sort_desc=True):
		'''Get the article history
		
		:see:
			`CMS.get_histories`
		
		:rtype: `list`
		'''
		
		return self._cms.get_histories(offset, limit, date_sort_desc, 
		article_id=self._model.id)


