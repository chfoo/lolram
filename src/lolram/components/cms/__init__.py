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

__docformat__ = 'restructuredtext en'

import os.path
import uuid
import datetime
import json
import time
import httplib
import mimetypes

from sqlalchemy import *
from sqlalchemy.orm import relationship
import sqlalchemy.sql
import sqlalchemy.orm

from lolram.components.base import BaseGlobalComponent, BaseComponent
from lolram.components.database import Database
from lolram.components.cms.dbdefs import CMSArticlesMeta, CMSArticleTreeMeta,\
	CMSHistoryMeta, CMSAddressesMeta, ArticleMetadataFields, ArticleViewModes,\
	CMSArticleMPTreeMeta
from lolram.dataobject import ProtectedObject
from lolram.models import BaseModel
from lolram.components.respool import ResPool
import iso8601
from lolram.components.cache import Cache
from lolram.components.accounts import AccountManager
from lolram.widgets import Document
from lolram.components.lion import Lion
from lolram2 import restpub

FILE_MAX = 32 ** 8 - 1
FILE_DIR_HASH = 997

ADD = 'A'
DEL = 'D'

class GlobalCMSManager(BaseGlobalComponent):
	def init(self):
		db = Database(self.context)
		db.add(CMSArticlesMeta, CMSArticleTreeMeta, CMSHistoryMeta,
			CMSAddressesMeta, CMSArticleMPTreeMeta)
		
		self._migration_needed = True
		
	def setup(self):
		cms_manager = GlobalCMSManager(self.context.global_context)
		
		if cms_manager._migration_needed:
			cms_manager._migration_needed = False
			db = Database(self.context)
			
			result = db.session.query(db.models.CMSArticleMPTree).first()
			
			if result:
				return
			
			query = db.session.query(db.models.CMSArticleTree)
			
			for model in query:
				new_model = db.models.CMSArticleMPTree()
				
				if model.parent_article_id:
					subquery = db.session.query(db.models.CMSArticleMPTree) \
						.filter_by(article_id=model.parent_article_id)
						
					mp_parent_model = subquery.first()
					
					if not mp_parent_model:
						mp_parent_model = db.models.CMSArticleMPTree()
						mp_parent_model.article_id = model.parent_article_id
						db.session.add(mp_parent_model)
					
					new_model.parent = mp_parent_model
					new_model.article_id = model.article_id
					
					db.session.add(new_model)
			

class CMS(BaseComponent):
	def __init__(self, *args, **kargs):
		super(BaseComponent, self).__init__(*args, **kargs)
		
		# FIXME: this should be in a seperate init function instead
		self._db = Database(self.context)
		self._acc = AccountManager(self.context)
		self._doc = Document(self.context)
		self._lion = Lion(self.context)
	
	def _restpub_template_callback(self, name):
		article = self.get_article(address=name)
		
		if article:
			return article.current.text
		
		article = self.get_article(uuid=uuid.UUID(name).bytes)
		
		if article:
			return article.current.text
	
	def _restpub_image_callback(self, name):
		article = self.get_article(address=name)
		
		if not article:
			try:
				bytes = uuid.UUID(name).bytes
				article = self.get_article(uuid=bytes)
			except ValueError:
				pass
		
		if not article:
			return name
		
		return self.context.str_url(fill_controller=True,
			args=[self.model_uuid_str(article.current)], params=self.RAW, )
	
	def _restpub_math_callback(self, hash, filename):
		basename = os.path.basename(filename)
		dest_dir = os.path.join(self.context.dirinfo.var, 'texvc', hash[0:2])
		
		if not os.path.exists(dest_dir):
			os.makedirs(dest_dir)
		
		dest_path = os.path.join(dest_dir, basename)
		
		if not os.path.exists(dest_path):
			os.rename(filename, dest_path)
		
		return self.context.str_url(fill_controller=True,
			args=[hash], params=self.TEXVC)
	
	def _restpub_internal_callback(self, *args, **kargs):
		if kargs.get('allow_intern'):
			return self.restpub_internal_callback(*args)
		else:
			# TODO: do something better than blow up
			raise Exception('For internal use only')
	
	def restpub_internal_callback(self, *args):
		raise NotImplementedError()
	
	def new_article(self):
		'''Create a new article
		
		:rtype: `ArticleWrapper`
		'''
		
		model = self._db.models.CMSArticle()
		model.account_id = self._acc.account_id
		return ArticleWrapper(self.context, model)
	
	def get_article(self, id=None, uuid=None, address=None):
		'''Get an article by its ID
		
		:rtype: `ArticleWrapper`
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
			return ArticleWrapper(self.context, model)
	
	def get_article_history(self, id=None, uuid=None):
		'''Get a single article history by ID
		
		:rtype: `ArticleHistoryReadWrapper`
		'''
		
		query = self._db.session.query(self._db.models.CMSHistory)
		
		if id:
			query = query.filter_by(id=id)
		else:
			query = query.filter_by(uuid=uuid)
	
		model = query.first()
		
		if model:
			return ArticleHistoryReadWrapper(self.context, model) 
	
	def get_articles(self, offset=0, limit=51, date_sort_desc=False):
		'''Get a list of articles
		
		:rtype: `list`
		:returns: a `list` of `ArticleWrapper`
		'''
		
		query = self._db.session.query(self._db.models.CMSArticle)
		
		if date_sort_desc:
			query = query.order_by(
				sqlalchemy.sql.desc(self._db.models.CMSArticle.date))
		else:
			query = query.order_by(self._db.models.CMSArticle.date)
		
		l = []
		
		for model in query[offset:offset+limit]:
			l.append(ArticleWrapper(self.context, model))
		
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
			ah = ArticleHistoryReadWrapper(self.context, model)
			ah._number = i
			l.append(ah)
			
			i += 1
		
		return l
	
	
	def run_maintenance(self):
		# TODO: clean up texvc files
		pass
	
	@classmethod
	def model_uuid_str(cls, model):
		return util.bytes_to_b32low(model.uuid_bytes)



class ArticleWrapper(ProtectedObject):
	def __init__(self, context, model):
		self._context = context
		self._model = model
		self._cms = CMS(context)
		self._db = Database(context)
		self._read_wrapper_cache = None
		
	def __hash__(self):
		return self._model.__hash__()
	
	def __cmp__(self, other):
		return self._model == other
	
	@property
	def id(self):
		'''Get the database ID'''
		
		return self._model.id
	
	@property
	def owner_account(self):
		return self._model.account
	
	@property
	def current(self):
		if not self._read_wrapper_cache and self._model.version:
			query = self._db.session.query(self._db.models.CMSHistory) \
				.filter_by(article_id=self.id) \
				.filter_by(version=self._model.version)
			
			model = query.first()
			
			if model:
				self._read_wrapper_cache = ArticleHistoryReadWrapper(self._context, model)
				
		return self._read_wrapper_cache
	
	@property
	def uuid(self):
		'''Get the UUID for this article
		
		The UUID encompasses the history set of this article
		
		:rtype: `uuid.UUID`
		'''
		
		return uuid.UUID(bytes=self._model.uuid)
	
	@property
	def uuid_bytes(self):
		return self._model.uuid
	
	@property
	def parents(self):
		return self.current.parents
	
	@property
	def children(self):
		query = self._db.session.query(self._db.models.CMSArticleMPTree) \
			.filter_by(article_id=self._model.id)
		
		tree_model = query.first()
		
		l = []
		
		if tree_model:
			for m in tree_model.mp.query_children():
				article = self._cms.get_article(id=m.article_id)
				
				if article:
					l.append(article)
		
		return frozenset(l)
	
	def get_children(self, offset=0, limit=50, sort_method='date', 
	sort_desc=False, include_descendants=False):
		query = self._db.session.query(self._db.models.CMSArticleMPTree) \
			.filter_by(article_id=self._model.id)
		
		tree_model = query.first()
		
		l = []
		
		if tree_model:
			col = self._db.models.CMSArticle.date
			
			if sort_method == 'title':
				col = self._db.models.CMSArticle.title
			
			if sort_desc:
				col = col.desc()
			
			if include_descendants:
				query = tree_model.mp.query_descendants()
			else:
				query = tree_model.mp.query_children()
			
			query = query \
				.join(self._db.models.CMSArticleMPTree.article) \
				.order_by(col) \
				.limit(limit).offset(offset)
			
			for m in query:
				article = self._cms.get_article(id=m.article_id)
				
				if article:
					l.append(article)
		
		return l
	
	def get_history(self, offset, limit=51, date_sort_desc=True):
		'''Get the article history
		
		:see:
			`CMS.get_histories`
		
		:rtype: `list`
		'''
		
		return self._cms.get_histories(offset, limit, date_sort_desc, 
		article_id=self._model.id)
	
	def edit(self):
		history_model = self._db.models.CMSHistory()
		history_model.article_id = self._model.id
		
		if self.current:
			past_history_model = self.current._model
			history_model.version = past_history_model.version + 1
			history_model.text_id = past_history_model.text_id
			history_model.file_id = past_history_model.file_id
			history_model.data_id = past_history_model.data_id
		else:
			history_model.version = 1
		
		return ArticleHistoryWriteWrapper(self._context, history_model, self)
	
	@property
	def title(self):
		return self._model.title
	
	@property
	def publish_date(self):
		return self._model.date
	
	@property
	def primary_address(self):
		return self._model.primary_address


class ArticleHistoryReadWrapper(ProtectedObject, BaseModel):
	def __init__(self, context, model):
		self._context = context
		self._model = model
		self._respool = ResPool(context)
		self._cms = CMS(context)
		self._db = Database(context)
		
		self._text = self._respool.get_text(model.text_id)
		self._data = json.loads(self._respool.get_text(model.data_id) or '{}')
		self._reason = self._respool.get_text(model.reason)
		self._file = self._respool.get_file(model.file_id)
		self._doc_info = None
		self._allow_intern = False
		
	@property
	def editor_account(self):
		return self._model.account_id
	
	@property
	def text(self):
		return self._text
	
	@property
	def metadata(self):
		return self._data
	
	@property
	def reason(self):
		return self._reason
	
	@property
	def file(self):
		return self._file
	
	@property
	def date(self):
		'''Get when the article was edited
		
		:rtype: `datetime.Datetime`
		'''
		
		return self._model.created
	
	@property
	def publish_date(self):
		o = self.metadata.get(ArticleMetadataFields.PUBLISH_DATE)
		
		if o and not isinstance(o, datetime.datetime):
			d = iso8601.parse_date(o)
			return util.datetime_to_naive(d)
		elif o:
			return o
	
	@property
	def title(self):
		return self.metadata.get(ArticleMetadataFields.TITLE)
	
	@property
	def addresses(self):
		return frozenset(self.metadata.get(ArticleMetadataFields.ADDRESSES, tuple()))
	
	@property
	def parents(self):
		l = []
		for s in self.metadata.get(ArticleMetadataFields.PARENTS, tuple()):
			article = self._cms.get_article(uuid=uuid.UUID(s).bytes)
			
			if article:
				l.append(article)
		
		return frozenset(l)
	
	@property
	def uuid(self):
		if self._model.uuid:
			return uuid.UUID(bytes=self._model.uuid)
	
	@property
	def uuid_bytes(self):
		return self._model.uuid
		
	@property
	def article(self):
		return self._cms.get_article(id=self._model.article_id)
	
	@property
	def version(self):
		return self._model.version
	
	@property
	def upload_filename(self):
		'''Get the originally uploaded filename'''
		return self.metadata.get(ArticleMetadataFields.FILENAME)
	
	@property
	def view_mode(self):
		return self.metadata.get(ArticleMetadataFields.VIEW_MODE)
	
	@property
	def primary_address(self):
		return self.metadata.get(ArticleMetadataFields.PRIMARY_ADDRESS)
	
	@property
	def doc_info(self):
		if self.text:
			cac = Cache(self._context)
			
			if self.uuid:
				self._doc_info = cac.get('cms%s' % self.uuid)
			else:
				self._doc_info = None
			
			if not self._doc_info:
				self._doc_info = restpub.publish_text(self.text,
					math_callback=self._cms._restpub_math_callback,
					internal_callback=self._cms._restpub_internal_callback,
					image_callback=self._cms._restpub_image_callback,
					template_callback=self._cms._restpub_template_callback,
					allow_intern=self._allow_intern,
				)
				
				if self.uuid:
					cac.set('cms%s' % self.uuid, self._doc_info)
		
		return self._doc_info


class ArticleHistoryWriteWrapper(ArticleHistoryReadWrapper):
	def __init__(self, context, model, article_wrapper):
		super(ArticleHistoryWriteWrapper, self).__init__(context, model)
		self._article_wrapper = article_wrapper
		
		if self.version == 1:
			# Defaults
			self.view_mode = ArticleViewModes.ALLOW_COMMENTS | ArticleViewModes.VIEWABLE
	
	@ArticleHistoryReadWrapper.text.setter
	def text(self, text):
		self._text = text
	
	@ArticleHistoryReadWrapper.reason.setter
	def reason(self, t):
		self._reason = t
	
	@ArticleHistoryReadWrapper.file.setter
	def file(self, f):
		self._file = f
	
	@ArticleHistoryReadWrapper.publish_date.setter
	def publish_date(self, d):
		self.metadata[ArticleMetadataFields.PUBLISH_DATE] = d
	
	@ArticleHistoryReadWrapper.addresses.setter
	def addresses(self, l):
		self.metadata[ArticleMetadataFields.ADDRESSES] = list(frozenset(l))
	
	@ArticleHistoryReadWrapper.parents.setter
	def parents(self, parents):
		l = []
		for article in parents:
			assert isinstance(article, ArticleWrapper)
			l.append(str(article.uuid))
		
		self.metadata[ArticleMetadataFields.PARENTS] = list(frozenset(l))
	
	@ArticleHistoryReadWrapper.upload_filename.setter
	def upload_filename(self, s):
		self.metadata[ArticleMetadataFields.FILENAME] = s
		
	@ArticleHistoryReadWrapper.view_mode.setter
	def view_mode(self, mode):
		self.metadata[ArticleMetadataFields.VIEW_MODE] = mode
		
	@ArticleHistoryReadWrapper.primary_address.setter
	def primary_address(self, s):
		self.metadata[ArticleMetadataFields.PRIMARY_ADDRESS] = s
	
	def save(self):
		assert self._text or self._file
		
		title = self.metadata.get(ArticleMetadataFields.TITLE)
		if not title and self.text:
			title = self.doc_info.title
		
		article_model = self._article_wrapper._model
		article_model.title = title \
			or self.metadata.get(ArticleMetadataFields.FILENAME) \
			or self.text[:160]
		article_model.date = self.publish_date \
			or article_model.date \
			or datetime.datetime.utcnow()
		article_model.view_mode = self.metadata.get(ArticleMetadataFields.VIEW_MODE)
		article_model.version = self._model.version
		article_model.primary_address = self.primary_address
		
		if not article_model.primary_address and self.addresses:
			self.primary_address = tuple(self.addresses)[0]
			article_model.primary_address = self.primary_address
		elif not self.addresses:
			article_model.primary_address = None
			self.primary_address = None
			
		if self.addresses:
			assert self.primary_address in self.addresses
		
		if article_model.primary_address:
			assert article_model.primary_address in self.addresses
		
		assert article_model.date
		assert article_model.title
		
		if not self._article_wrapper._model.id:
			self._db.session.add(self._article_wrapper._model)
			self._db.session.flush()
			self._model.article_id = self._article_wrapper._model.id
		
		if self._text:
			self._model.text_id = self._respool.set_text(self._text, create=True)
		
		if self._reason:
			self._model.reason = self._respool.set_text(self._reason, create=True)
		
		if self._file:
			self._model.file_id = self._respool.set_file(self._file, create=True)
		
		if self._data:
			self._model.data_id = self._respool.set_text(
				json.dumps(self._data), create=True)
		
		query = self._db.session.query(self._db.models.CMSAddress) \
			.filter_by(article_id=article_model.id)
		
		if self.addresses:
			# If this condition is removed, then contradictions may occur
			query = query.filter(~self._db.models.CMSAddress.name.in_(self.addresses)) \
			
		query.delete(synchronize_session='fetch')
		
		query = self._db.session.query(self._db.models.CMSAddress.name)
		query = query.filter_by(article_id=self._model.article_id)
		
		addresses_to_insert = self.addresses - frozenset([r[0] for r in query])
		
		for address in addresses_to_insert:
			model = self._db.models.CMSAddress()
			self._db.session.add(model)
			model.name = address
			model.article = self._article_wrapper._model
		
		parent_article_ids = set([m.id for m in self.parents])
		
		query = self._db.session.query(self._db.models.CMSArticleMPTree) \
			.filter_by(article_id=self._model.article_id)
		
#		if parent_article_ids:
#			# If this this condition is removed, contradictions may occur
#			query = query.filter(~self._db.models.CMSArticleMPTree.parent.article_id.in_(
#				parent_article_ids))
		
		for tree_model in query:
			tree_model.parent = None
			self._db.session.delete(tree_model)
		
		query = self._db.session.query(self._db.models.CMSArticleMPTree) \
			.filter_by(article_id=self._model.article_id)
		
		parent_ids_to_insert = parent_article_ids \
			- frozenset([model.parent_article_id for model in query])
		
		for article_id in parent_ids_to_insert:
			query = self._db.session.query(self._db.models.CMSArticleMPTree) \
				.filter_by(article_id=article_id)
			
			parent_tree_model = query.first()
			if not parent_tree_model:
				parent_tree_model = self._db.models.CMSArticleMPTree()
				self._db.session.add(parent_tree_model)
				parent_tree_model.article_id = article_id
			
			new_tree_model = self._db.models.CMSArticleMPTree(parent=parent_tree_model)
			new_tree_model.article_id = self._model.article_id
#			new_tree_model.parent_article_id = article_id
			self._db.session.add(new_tree_model)
		
		acc = AccountManager(self._context)
		self._model.account_id = acc.account_id
		self._db.session.add(self._model)
		
		query = self._db.session.query(self._db.models.CMSArticleTree) \
			.filter_by(article_id=self._model.article_id) \
			.filter_by(parent_article_id=0)
		
		tree_model = query.first()
		
		if not tree_model:
			tree_model = self._db.models.CMSArticleTree()
			tree_model.parent_article_id = 0
			tree_model.article_id = self._model.article_id
			self._db.session.add(tree_model)
		

	
	