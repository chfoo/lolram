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


import lxml.html.builder as lxmlbuilder
import lxml.html

import base
import database
import accounts
import wui
import respool
import dbutil.nestedsets
from .. import dataobject
from .. import configloader
from .. import iso8601
from .. import restpub
from .. import models
from .. import util
from .. import views

FILE_MAX = 32 ** 8 - 1
FILE_DIR_HASH = 997

ADD = 'A'
DEL = 'D'

class ActionRole(object):
	NAMESPACE = 'lr-cms'
	VIEWER = 1
	COMMENTER = 3
	WRITER = 4
	MODERATOR = 5
	CURATOR = 6
	BUREAUCRAT = 7
	BOT = 8

class ArticleViewModes(object):
	VIEWABLE = 0b1
	
	TEXT = 0b00
	FILE = 0b10
	
	ARTICLE = 0b100
	COMMENT = 0b000
	
	ALLOW_COMMENTS = 0b1000
	
	CATEGORY = 0b10000

class ArticleActions(object):
	COMMENT_ON_TEXT = 'comment'
	EDIT_TEXT = 'edit'
	VIEW_TEXT = 'view'
	EDIT_TEXT_PROPERTIES = 'edit-properties'
	VIEW_HISTORY = 'view-history'

class ArticleMetadataFields(object):
	PUBLISH_DATE = 'pubdate'
	TITLE = 'title'
	FILENAME = 'filename'
	MIMETYPE = 'mimetype'
	FILETYPE = 'filetype'
	PARENTS = 'parents'
	ADDRESSES = 'addresses'
	VIEW_MODE = 'viewmode'

class CMSArticlesMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSArticle(database.TableMeta.Def.base()):
			__tablename__ = 'cms_articles'
			
			id = Column(Integer, primary_key=True)
			account_id = Column(ForeignKey(accounts.AccountsMeta.D1.Account.id))
			account = relationship(accounts.AccountsMeta.D1.Account)
			date = Column(DateTime, default=datetime.datetime.utcnow)
			title = Column(Unicode(length=160))
			uuid = Column(LargeBinary(length=16), default=lambda:uuid.uuid4().bytes, index=True)
			view_mode = Column(Integer)
			version = Column(Integer, nullable=False)
			primary_address = Column(Unicode(length=160))
		
		desc = 'new table'
		model = CMSArticle
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)

	uuid = 'urn:uuid:f9d34d49-5226-48a1-a115-3c07de711071'
	defs = (D1, )

ResPoolText = respool.ResPoolTextMeta.D1.ResPoolText
ResPoolFile = respool.ResPoolFileMeta.D1.ResPoolFile

class CMSHistoryMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSHistory(database.TableMeta.Def.base()):
			__tablename__ = 'cms_history'
			
			article_id = Column(ForeignKey(CMSArticlesMeta.D1.CMSArticle.id),
				primary_key=True)
			article = relationship(CMSArticlesMeta.D1.CMSArticle)
			version = Column(Integer, primary_key=True)
			text_id = Column(ForeignKey(ResPoolText.id))
			data_id = Column(ForeignKey(ResPoolText.id))
			file_id = Column(ForeignKey(ResPoolFile.id))
			reason = Column(ForeignKey(ResPoolText.id))
			created = Column(DateTime, default=datetime.datetime.utcnow)
			uuid = Column(LargeBinary(length=16), default=lambda:uuid.uuid4().bytes, index=True)
			account_id = Column(ForeignKey(accounts.AccountsMeta.D1.Account.id))
			account = relationship(accounts.AccountsMeta.D1.Account)
			
		desc = 'new table'
		model = CMSHistory
	
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)

	uuid = 'urn:uuid:597f9776-3e38-4c91-87fd-295f1b8ab29d'
	defs = (D1,)


class CMSAddressesMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSAddress(database.TableMeta.Def.base()):
			__tablename__ = 'cms_addresses'
			
			id = Column(Integer, primary_key=True)
			name = Column(Unicode(length=160), nullable=False, unique=True, index=True)
			article_id = Column(ForeignKey(CMSArticlesMeta.D1.CMSArticle.id),
				nullable=False)
			article = relationship(CMSArticlesMeta.D1.CMSArticle, 
				collection_class=set)
		
		desc = 'new table'
		model = CMSAddress
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)

	uuid = 'urn:uuid:02e2bb62-81c2-4b50-8417-e26d3011da61'
	defs = (D1,)


class CMSArticleTreeMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSArticleTree(database.TableMeta.Def.base()):
			__tablename__ = 'cms_article_tree'
			
			article_id = Column(ForeignKey(CMSArticlesMeta.D1.CMSArticle.id), 
				primary_key=True)
			article = relationship(CMSArticlesMeta.D1.CMSArticle,
				primaryjoin=article_id==CMSArticlesMeta.D1.CMSArticle.id)
			parent_article_id = Column(ForeignKey(CMSArticlesMeta.D1.CMSArticle.id),
				primary_key=True)
			parent_article = relationship(CMSArticlesMeta.D1.CMSArticle,
				primaryjoin=article_id==CMSArticlesMeta.D1.CMSArticle.id)
			
			@property
			def children(self):
				session = sqlalchemy.orm.session.Session.object_session(self)
				query = session.query(self.__class__) \
					.filter_by(parent_article_id=self.article_id)
				return query
	
		desc = 'new table'
		model = CMSArticleTree
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)
		


	uuid = 'urn:uuid:b4227b69-c4ce-47e6-910a-e5b9f7c1f8df'
	defs = (D1,)


class CMS(base.BaseComponent):
	GET = 'g'
	GET_VERSION = 'v'
	BROWSE = 'b'
	ALL = 'a'
	ARTICLES = 't'
	FILES = 'f'
	HISTORY = 'h'
	NEW = 'n'
	EDIT = 'e'
	UPLOAD = 'u'
	RAW = 'r'
	EDIT_VIEW = 'd'
	TEXVC = 'x'
	
	def init(self):
		db = self.context.get_instance(database.Database)
		db.add(CMSArticlesMeta, CMSArticleTreeMeta, CMSHistoryMeta,
			CMSAddressesMeta)
		
		acc = self.context.get_instance(accounts.Accounts)
		acc.register_role(ActionRole.NAMESPACE, 
			ActionRole.COMMENTER,
			ActionRole.WRITER,
			ActionRole.MODERATOR,
			ActionRole.VIEWER,
			ActionRole.BOT,
			ActionRole.CURATOR,
		)
	
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
			args=(self.RAW, self.model_uuid_str(article.current)))
	
	def _restpub_math_callback(self, hash, filename):
		basename = os.path.basename(filename)
		dest_dir = os.path.join(self.context.dirinfo.var, 'texvc', hash[0:2])
		
		if not os.path.exists(dest_dir):
			os.makedirs(dest_dir)
		
		dest_path = os.path.join(dest_dir, basename)
		
		if not os.path.exists(dest_path):
			os.rename(filename, dest_path)
		
		return self.context.str_url(fill_controller=True,
			args=(self.TEXVC, hash)
		)
	
	def _restpub_internal_callback(self, *args):
		return 'not implemented'
	
	def setup(self):
		self._db = self.context.get_instance(database.Database)
		self._cms = self.context.get_instance(CMS)
		self._acc = self.context.get_instance(accounts.Accounts)
		self._doc = self.context.get_instance(wui.Document)
	
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
	
	def serve(self):
		arg1 = None
		arg2 = None
		
		if len(self.context.request.args) >= 1:
			arg1 = self.context.request.args[0]
		if len(self.context.request.args) == 2:
			arg2 = self.context.request.args[1]
		elif len(self.context.request.args) > 2:
			arg1 = None
			arg2 = None
		
		self._doc.title = 'test %s %s' % (arg1, arg2)
		
		if arg1 and not arg2:
			article = self.get_article(address=arg1)
			
			if article:
				if self._check_permissions(ArticleActions.VIEW_TEXT, article.current):
					self.context.response.set_status(403)
					return
				
				self.context.response.ok()
				
				if article.current.view_mode & ArticleViewModes.CATEGORY:
					nested_count = -1
				else:
					nested_count = 5
				
				self._build_article_page(article.current, nested_count)
				
				if article.current.view_mode & ArticleViewModes.CATEGORY:
					self._build_single_article_listing(article)
				
		elif arg1 == self.GET and arg2:
			uuid_bytes = util.b32low_to_bytes(arg2)
			article = self.get_article(uuid=uuid_bytes)
			
			if article:
				if self._check_permissions(ArticleActions.VIEW_TEXT, article.current):
					self.context.response.set_status(403)
					return
				
				self.context.response.ok()
				
				if article.current.view_mode & ArticleViewModes.CATEGORY:
					nested_count = -1
				else:
					nested_count = 5
				
				self._build_article_page(article.current, nested_count)
				
				if article.current.view_mode & ArticleViewModes.CATEGORY:
					self._build_single_article_listing(article)
				
				if article.primary_address:
					self.context.response.headers.add('Link', 
						u'<%s>' % self.context.str_url(fill_controller=True,
							args=[article.primary_address]), rel='Canonical')
		
		elif arg1 == self.GET_VERSION and arg2:
			uuid_bytes = util.b32low_to_bytes(arg2)
			article = self.get_article_history(uuid=uuid_bytes)
			
			if article:
				if self._check_permissions(ArticleActions.VIEW_HISTORY, article):
					self.context.response.set_status(403)
					return
				
				self.context.response.ok()
				self._build_article_version(article)
		
		elif arg1 == self.BROWSE and arg2:
			self.context.response.ok()
			
			if arg2 == self.ARTICLES:
				self._build_article_listing(True, False)
			elif arg2 == self.FILES:
				self._build_article_listing(False, True)
			else:
				self._build_article_listing()
		
		elif arg1 == self.HISTORY and arg2:
			uuid_bytes = util.b32low_to_bytes(arg2)
			article = self.get_article(uuid=uuid_bytes)
			
			if article:
				self.context.response.ok()
				self._build_article_history_listing(article)
		
		elif arg1 in (self.EDIT, self.UPLOAD) and arg2:
			edit_type = self.FILES
			
			if arg1 == self.UPLOAD:
				edit_type = self.UPLOAD
			
			if arg2 != self.NEW:
				uuid_bytes = util.b32low_to_bytes(arg2)
				article = self.get_article(uuid=uuid_bytes)
				article_version = article.edit()
				
				if self._check_permissions(ArticleActions.EDIT_TEXT, article_version):
					self.context.response.set_status(403)
					return
			else:
				article = self.new_article()
				article_version = article.edit()
				
			self.context.response.ok()
			
			if arg1 == self.EDIT:
				if (article_version.text or 'text' in self.context.request.form)\
				and not 'submit-publish' in self.context.request.form:
					# FIXME: due to dependencies, text must be set for previewer
					article_version.text = self.context.request.form.getfirst('text', article_version.text)
					self._build_article_preview(article_version)
				
				self._build_article_edit_page(article_version)
			else:
				self._build_upload_page(article_version)
		
		elif arg1 == self.RAW and arg2:
			uuid_bytes = util.b32low_to_bytes(arg2)
			article = self.get_article_history(uuid=uuid_bytes)
			
			if article:
				if self._check_permissions(ArticleActions.VIEW_TEXT, article):
					self.context.response.set_status(403)
					return
				
				self.context.response.ok()
				
				if article.article.primary_address:
					self.context.response.headers.add('Link', 
						u'<%s>' % self.context.str_url(fill_controller=True,
							args=[article.article.primary_address]), 
								rel='Canonical')
				
				return self._serve_raw(article)
		
		elif arg1 == self.EDIT_VIEW and arg2:
			uuid_bytes = util.b32low_to_bytes(arg2)
			article = self.get_article(uuid=uuid_bytes)
			article_version = article.edit()
			
			if self._check_permissions(ArticleActions.EDIT_TEXT_PROPERTIES, article_version):
				self.context.response.set_status(403)
				return
			
			self.context.response.ok()
			self._build_article_edit_view_page(article_version)
		
		elif arg1 == self.TEXVC and arg2:
			dest_dir = os.path.join(self.context.dirinfo.var, 'texvc', arg2[0:2])
			dest_path = os.path.join(dest_dir, '%s.png' % arg2)
		
			return self.context.response.output_file(dest_path)
	
	def _build_article_page(self, article, nested_count=5):
		self._doc.title = article.title or article.upload_filename
		
		if article.doc_info:
			self._doc.title = article.doc_info.title
			self._doc.meta.subtitle = article.doc_info.subtitle
			
			for k, v in article.doc_info.meta.iteritems():
				if v is not None:
					self._doc.meta[k] = v
		
		self._doc.append(dataobject.MVPair(article, nested_count=nested_count))
	
	def _build_article_version(self, article_history):
		self._doc.title = u'Viewing past version %s: %s' % \
			(article_history.version, 
			article_history.title or article_history.upload_filename)
		self._doc.append(dataobject.MVPair(article_history, 
			article_format=ArticleView.ARTICLE_FORMAT_SINGLE))
	
	def _build_article_preview(self, article_history):
		doc_info = article_history.doc_info
		
		if article_history.title:
			self._doc.title = u'Editing %s' % article_history.title
		
		self._doc.add_message(u'This is only a preview', 'Your changes have not been saved!')
		
		if doc_info and doc_info.errors:
			self._doc.add_message(u'There are syntax errors in the document',
				doc_info.errors)
		
		self._doc.append(dataobject.MVPair(article_history, 
			article_format=ArticleView.ARTICLE_FORMAT_PREVIEW))
	
	def _build_article_listing(self, show_articles=True, show_files=True):
		page_info = self.context.page_info(limit=50)
		articles = self.get_articles(page_info.offset, page_info.limit + 1,
			date_sort_desc=True)
		
		table = models.Table()
		table.headers = ('Title', 'Date')
		
		counter = 0
		for article in articles:
			table.rows.append((
				(article.title or article.current.upload_filename or '(untitled)', 
					self.context.str_url(fill_controller=True,
					args=(CMS.GET, util.bytes_to_b32low(article.uuid.bytes),))), 
				str(article.publish_date), 
			))
			
			counter += 1
			if counter > 50:
				page_info.more = True
				break
		
		self._doc.append(dataobject.MVPair(page_info, views.PagerView))
		self._doc.append(dataobject.MVPair(table, 
			row_views=(views.LabelURLToLinkView, None)))
		self._doc.append(dataobject.MVPair(page_info, views.PagerView))
	
	def _build_single_article_listing(self, article):
		page_info = self.context.page_info(limit=50)
		sort_method = self.context.request.query.getfirst('s', 'date')
		sort_desc = self.context.request.query.getfirst('o')
		children = article.get_children(page_info.offset, page_info.limit + 1,
			sort_method=sort_method, sort_desc=sort_desc,
		)
		
		table = models.Table()
		table.headers = ('Title', 'Date')
		
		counter = 0
		for article in children:
			table.rows.append((
				(article.title or article.current.upload_filename or '(untitled)', 
					self.context.str_url(fill_controller=True,
					args=(CMS.GET, util.bytes_to_b32low(article.uuid.bytes),))), 
				str(article.publish_date), 
			))
			
			counter += 1
			if counter > page_info.limit:
				page_info.more = True
				break
		
		self._doc.append(dataobject.MVPair(table, 
			row_views=(views.LabelURLToLinkView, None)))
		self._doc.append(dataobject.MVPair(page_info, views.PagerView))
	
	def _build_article_history_listing(self, article):
		page_info = self.context.page_info(limit=50)
			
		table = models.Table()
		table.header = ('Version', 'Date', 'Title')
				
		counter = 0
		for info in article.get_history(page_info.offset, page_info.limit):
			url = self.context.str_url(fill_controller=True,
				args=(self.GET_VERSION, CMS.model_uuid_str(info)))
			
			table.rows.append((
				str(info.version), 
				str(info.date), 
				(info.title or info.upload_filename or '(untitled)', url),
			))
					
			counter += 1
			if counter > 50:
				page_info.more = True
				break
		
		self._doc.append(dataobject.MVPair(page_info, views.PagerView))
		self._doc.append(dataobject.MVPair(table, 
			row_views=(None, None, views.LabelURLToLinkView)))
		self._doc.append(dataobject.MVPair(page_info, views.PagerView))
	
	def _serve_raw(self, article_history):
		self.context.response.headers['last-modified'] = str(article_history.date)
				
		if article_history.text:
			self.context.response.set_content_type('text/plain')
			return [article_history.text.encode('utf8')]
		else:
			return self.context.response.output_file(
				article_history.file.filename,
				download_filename=article_history.upload_filename)
	
	def _build_upload_page(self, article_version):
		form = models.Form(models.Form.POST, 
			self.context.str_url(fill_path=True, 
				fill_args=True, fill_params=True, fill_query=True))
		
		if 'submit-publish' in self.context.request.form:
			address = self.context.request.form.getfirst('address')
			article_version.upload_filename = self.context.request.form['file'].filename
			article_version.file = self.context.request.form['file'].file
			article_version.reason = self.context.request.form.getfirst('reason')
			
			if not article_version.addresses and address:
				article_version.addresses = article_version.addresses | \
					frozenset([address])
			
			article_version.view_mode = ArticleViewModes.FILE | ArticleViewModes.VIEWABLE
			article_version.save()
			
			self._doc.add_message('Upload was a success')
			
			return
		
#		self._doc.add_message('Please name your file uniquely and carefully')
		
		if not article_version.addresses:
			form.textbox('address', 'Address (optional):')
		
		form.textbox('file', 'File:', validation=form.Textbox.FILE, required=True)
		form.textbox('reason', 'Reason or changes (optional):')
		form.button('submit-publish', 'Upload')
		
		self._doc.append(dataobject.MVPair(form))
		
	
	def _build_article_edit_page(self, article_version):
		form = models.Form(models.Form.POST, 
			self.context.str_url(fill_path=True, 
				fill_args=True, fill_params=True, fill_query=True))
		
		if 'submit-publish' in self.context.request.form:
			
			article_version.text = self.context.request.form.getfirst('text')
			address = self.context.request.form.getfirst('address')
			article_version.reason = self.context.request.form.getfirst('reason')
			
			doc_info = article_version.doc_info
			
			date = doc_info.meta.get('date')
			if date:
				article_version.publish_date = date
			
			article_version.metadata[ArticleMetadataFields.TITLE] = (doc_info.title or article_version.text)[:160]
			article_version.view_mode = ArticleViewModes.TEXT | ArticleViewModes.ALLOW_COMMENTS | ArticleViewModes.VIEWABLE
			
			if self._acc.is_authorized(ActionRole.NAMESPACE, ActionRole.WRITER):
				if not article_version.addresses and address:
					article_version.addresses = article_version.addresses | \
						frozenset([address])
				
				if 'is-article' in self.context.request.form:
					article_version.view_mode = article_version.view_mode | ArticleViewModes.ARTICLE
			
			parent_str = self.context.request.form.getfirst('parent')
			
			if parent_str:
				uuid_bytes = util.b32low_to_bytes(parent_str)
				parent_article = self.get_article(uuid=uuid_bytes)
				
				article_version.parents |= frozenset([parent_article])
				
				if self._check_permissions(ArticleActions.COMMENT_ON_TEXT, article_version):
					self.context.response.set_status(403)
					return
			else:
				if self._check_permissions(ArticleActions.EDIT_TEXT, article_version):
					self.context.response.set_status(403)
					return
			
			article_version.reason = self.context.request.form.getfirst('reason')
			article_version.save()
			
			self._doc.add_message('Edit was a success')
			
			return
		
		text = ''
		if 'submit-preview' not in self.context.request.form:
			# XXX must be pure unicode otherwise lxml complains
			text = unicode(article_version.text or '')
		
		if not article_version.addresses \
		and self._acc.is_authorized(ActionRole.NAMESPACE, ActionRole.WRITER):
			form.textbox('address', 'Address (optional):')
		
		if self._acc.is_authorized(ActionRole.NAMESPACE, ActionRole.WRITER):
			opts = form.options('is-article', 'View mode article')
			opts.option('true', 'Yes', active=True)
		
		form.textbox('text', 'Article content:', text, large=True, required=True)
		form.textbox('reason', 'Reason for edit (optional):')
		form.button('submit-publish', 'Publish')
		form.button('submit-preview', 'Preview')
		
		self._doc.append(dataobject.MVPair(form))
	
	def _build_article_edit_view_page(self, article_history):
		if article_history.view_mode is None:
			article_history.view_mode = 0
		
		form = models.Form(models.Form.POST, 
			self.context.str_url(fill_path=True, 
				fill_args=True, fill_params=True, fill_query=True))
		
		if 'submit' in self.context.request.form:
			address = self.context.request.form.getfirst('address')
			addresses = self.context.request.form.getfirst('addresses')
			addresses = filter(None, addresses.splitlines())
			parents = self.context.request.form.getfirst('parents')
			parents = filter(None, parents.splitlines())
			
			article_history.addresses = frozenset(addresses)
			if address:
				article_history.article._model.primary_address = address
			
			parent_list = []
			for uuid_hex in parents:
				parent = self.get_article(uuid=uuid.UUID(uuid_hex).bytes)
				parent_list.append(parent)
			
			article_history.parents = frozenset(parent_list)
			
			view_modes = self.context.request.form.getlist('view-modes')
			article_history.view_mode = 0
			
			# FIXME: better table lookup
			d = {
				'text': ArticleViewModes.TEXT,
				'file': ArticleViewModes.FILE,
				'article': ArticleViewModes.ARTICLE,
				'comment': ArticleViewModes.COMMENT,
				'category': ArticleViewModes.CATEGORY,
				'viewable': ArticleViewModes.VIEWABLE,
				'comments': ArticleViewModes.ALLOW_COMMENTS,
			}
			
			for mode in view_modes:
				v = d[mode]
				article_history.view_mode = article_history.view_mode | v
			
			article_history.reason = self.context.request.form.getfirst('reason')
			article_history.save()
			
			self._doc.add_message('Changes have been saved')
			
			return
		
		form.textbox('address', 'Prefered address', 
			article_history.article.primary_address or '')
		form.textbox('addresses', 'Addresses', 
			u'\n'.join(article_history.addresses), large=True)
		form.textbox('parents', 'Parents', 
			u'\n'.join([a.uuid.urn for a in article_history.parents]), 
			large=True)
		
		opts = form.options('view-modes', 'View Modes', multi=True)
		opts.option('text', 'Text', 
			article_history.view_mode & ArticleViewModes.TEXT)
		opts.option('file', 'File', 
			article_history.view_mode & ArticleViewModes.FILE)
		opts.option('article', 'Is an article', 
			article_history.view_mode & ArticleViewModes.ARTICLE)
		opts.option('comment', 'Is a comment', 
			article_history.view_mode & ArticleViewModes.COMMENT)
		opts.option('category', 'Is a category', 
			article_history.view_mode & ArticleViewModes.CATEGORY)
		opts.option('viewable', 'Viewable', 
			article_history.view_mode & ArticleViewModes.VIEWABLE)
		opts.option('comments', 'Allow comments', 
			article_history.view_mode & ArticleViewModes.ALLOW_COMMENTS)
		
		form.textbox('reason', 'Reason for edit (optional):')
		form.button('submit', 'Save')
		
		self._doc.append(dataobject.MVPair(form))

	
	def _check_permissions(self, action, article_history):
		if action == ArticleActions.VIEW_TEXT \
		and not article_history.view_mode & ArticleViewModes.VIEWABLE:
			self._doc.add_message('Sorry, you may not view this article')
			return True
		
		if action == ArticleActions.VIEW_HISTORY \
		and not article_history.view_mode & ArticleViewModes.ARTICLE \
		and not self._acc.is_authorized(ActionRole.NAMESPACE, ActionRole.MODERATOR) \
		and not article_history.article.owner_account.id == self._acc.account_id:
			self._doc.add_message(u'Sorry, you may not view this article’s history')
			return True
		
		if action == ArticleActions.COMMENT_ON_TEXT \
		and not self._acc.is_authorized(ActionRole.NAMESPACE, ActionRole.COMMENTER) \
		and not article_history.view_mode & ArticleViewModes.COMMENT:
			self._doc.add_message(u'Sorry, you may not post comments on this article')
			return True
		
		if action == ArticleActions.EDIT_TEXT \
		and ((not self._acc.is_authorized(ActionRole.NAMESPACE, ActionRole.MODERATOR) \
		and article_history.article \
		and not article_history.article.owner_account.id == self._acc.account_id) \
		or (not article_history.view_mode & ArticleViewModes.ARTICLE \
		and not self._acc.is_authorized(ActionRole.NAMESPACE, ActionRole.WRITER))):
			self._doc.add_message(u'Sorry, you may not edit this article')
			return True
		
		if action == ArticleActions.EDIT_TEXT_PROPERTIES \
		and (not self._acc.is_authorized(ActionRole.NAMESPACE, ActionRole.CURATOR) \
		and not article_history.article.owner_account.id == self._acc.account_id):
			self._doc.add_message(u'Sorry, you may not edit this article’s properties')
			return True
		
		return False
	
	@classmethod
	def model_uuid_str(cls, model):
		return util.bytes_to_b32low(model.uuid.bytes)

class ArticleView(dataobject.BaseView):
	PLAIN_TEXT = 'plain'
	RESTRUCTUREDTEXT = 'rest'
	
	ARTICLE_FORMAT_PREVIEW = 'preview'
	ARTICLE_FORMAT_SINGLE = 'single'
	ARTICLE_FORMAT_NORMAL = 'normal'
	
	@classmethod
	def to_html(cls, context, model, article_format=ARTICLE_FORMAT_NORMAL, nested_count=-1, is_nested_child=False):
		element = lxmlbuilder.E.article(CLASS='article')
		
		if article_format in (cls.ARTICLE_FORMAT_NORMAL, cls.ARTICLE_FORMAT_SINGLE):
			element.set('id', CMS.model_uuid_str(model.article))
			
			element.append(cls.build_article_brief_metadata(context, model, is_nested_child))
		
		if model.text:
			doc_info = model.doc_info
			assert doc_info
			
			
#			meta_table = lxmlbuilder.TABLE()
#			
#			for n, v in doc_info.meta.iteritems():
#				tr = lxmlbuilder.TR(
#					lxmlbuilder.TH(n), lxmlbuilder.TD(v)
#				)
#				meta_table.append(tr)
#			
#			element.append(meta_table)
			
			if doc_info.errors:
				element.append(lxmlbuilder.PRE(unicode(model.text)))
			else:
				if article_format == cls.ARTICLE_FORMAT_SINGLE:
					element.append(lxml.html.fromstring(
						doc_info.html_parts['body_pre_docinfo'] or '<div></div>')
					)
				
				element.extend([
					lxml.html.fromstring(
						doc_info.html_parts['docinfo'] or '<div></div>'),
					lxml.html.fromstring(
						doc_info.html_parts['fragment'] or '<div></div>'),
					])
		
		elif model.file:
			url = context.str_url(fill_controller=True, 
				args=[CMS.RAW, CMS.model_uuid_str(model)])
			
			element.append(lxmlbuilder.IMG(src=url)) 
			
		if article_format == cls.ARTICLE_FORMAT_SINGLE:
			element.append(cls.build_article_detailed_metadata(context, model))
		
		ul = lxmlbuilder.UL(CLASS='articleActions')
		
		def add(label, url):
			ul.append(lxmlbuilder.LI(lxmlbuilder.A(label, href=url)))
		
		if article_format in (cls.ARTICLE_FORMAT_NORMAL, cls.ARTICLE_FORMAT_SINGLE):
			add('Raw', context.str_url(
				args=(CMS.RAW, CMS.model_uuid_str(model)),
				fill_controller=True,
			))
		
		if article_format == cls.ARTICLE_FORMAT_NORMAL:
			add('Edit', context.str_url(
				args=(CMS.EDIT if model.text else CMS.UPLOAD, 
					CMS.model_uuid_str(model.article)),
				fill_controller=True,
			))
			add('Admin', context.str_url(
				args=(CMS.EDIT_VIEW, 
					CMS.model_uuid_str(model.article)),
				fill_controller=True,
			))
			add('History', context.str_url(
				args=(CMS.HISTORY, CMS.model_uuid_str(model.article)),
				fill_controller=True,
			))
			add('Reply', context.str_url(
				args=(CMS.EDIT, CMS.NEW),
				fill_controller=True, 
					query=dict(parent=CMS.model_uuid_str(model.article))
			))
		elif article_format ==  cls.ARTICLE_FORMAT_SINGLE:
			add(u'View current version', context.str_url(
				args=(CMS.GET, CMS.model_uuid_str(model.article),),
				fill_controller=True,
			))
		
		element.append(ul)
		
		if article_format == cls.ARTICLE_FORMAT_NORMAL and nested_count > -1:
			page_info = context.page_info(limit=50)
			children = model.article.get_children(page_info.offset, page_info.limit + 1)
			
			counter = 0
			for child_article in children:
				element.append(cls.to_html(context, child_article.current, 
					nested_count=(nested_count - 1), is_nested_child=True,
					))
				
				counter += 1
				if counter > page_info.limit:
					page_info.more = True
					break
			
			element.append(views.PagerView.to_html(context, page_info))
			
		elif article_format == cls.ARTICLE_FORMAT_NORMAL and model.article.children:
			element.append(lxmlbuilder.A('(More)', href=
				context.str_url(
				args=(CMS.GET, CMS.model_uuid_str(model.article),),
				fill_controller=True,)
			))
		
		return element
	
	@classmethod
	def build_article_brief_metadata(cls, context, model, is_nested_child):
		date = '(%s)' % (model.publish_date or model.date)
		author_name = '(unknown)'
		
		if model._model.account and model._model.account.nickname:
			author_name = model._model.account.nickname
		
		ul = lxmlbuilder.UL(
			lxmlbuilder.LI(date),
			lxmlbuilder.LI(author_name),
			lxmlbuilder.CLASS('articleBriefMetadata')
		)
		
		for parent_model in model.parents:
			label = u'In reply to “%s”' % (parent_model.title or parent_model.upload_filename or '(untitled')
			
			if is_nested_child:
				url = '#%s' % CMS.model_uuid_str(parent_model)
			else:
				url = context.str_url(fill_controller=True,
					args=(CMS.GET, CMS.model_uuid_str(parent_model)))
			
			ul.insert(0, lxmlbuilder.LI(lxmlbuilder.A(label, href=url)))
		
		return ul
	
	@classmethod
	def build_article_detailed_metadata(cls, context, model):
		ul = lxmlbuilder.UL(
			lxmlbuilder.LI('Article ' +model.article.uuid.urn),
			lxmlbuilder.LI('Version ' +model.uuid.urn),
			lxmlbuilder.CLASS('articleDetailedMetadata')
		)
		
		if model.file:
			ul.append(lxmlbuilder.LI(
				model.metadata.get(ArticleMetadataFields.MIMETYPE, '')))
			ul.append(lxmlbuilder.LI(
				model.metadata.get(ArticleMetadataFields.FILETYPE, '')))
			ul.append(lxmlbuilder.LI(model.file.hash.encode('hex')))
		
		return ul	


class ArticleWrapper(dataobject.ProtectedObject):
	def __init__(self, context, model):
		self._context = context
		self._model = model
		self._cms = context.get_instance(CMS)
		self._db = context.get_instance(database.Database)
		
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
		if self._model.version:
			query = self._db.session.query(self._db.models.CMSHistory) \
				.filter_by(article_id=self.id) \
				.filter_by(version=self._model.version)
			
			model = query.first()
			
			if model:
				return ArticleHistoryReadWrapper(self._context, model)
	
	@property
	def uuid(self):
		'''Get the UUID for this article
		
		The UUID encompasses the history set of this article
		
		:rtype: `uuid.UUID`
		'''
		
		return uuid.UUID(bytes=self._model.uuid)
	
	@property
	def parents(self):
		return self.current.parents
	
	@property
	def children(self):
		query = self._db.session.query(self._db.models.CMSArticleTree) \
			.filter_by(article_id=self._model.id)
		
		tree_model = query.first()
		
		l = []
		
		if tree_model:
			for m in tree_model.children:
				article = self._cms.get_article(id=m.article_id)
				
				if article:
					l.append(article)
		
		return frozenset(l)
	
	def get_children(self, offset=0, limit=50, sort_method='date', sort_desc=False):
		query = self._db.session.query(self._db.models.CMSArticleTree) \
			.filter_by(article_id=self._model.id)
		
		tree_model = query.first()
		
		l = []
		
		if tree_model:
			col = self._db.models.CMSArticle.date
			
			if sort_method == 'title':
				col = self._db.models.CMSArticle.title
			
			if sort_desc:
				col = col.desc()
			
			query = tree_model.children \
				.join(self._db.models.CMSArticleTree.article) \
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
		
class ArticleHistoryReadWrapper(dataobject.ProtectedObject, dataobject.BaseModel):
	default_view = ArticleView
	
	def __init__(self, context, model):
		self._context = context
		self._model = model
		self._respool = context.get_instance(respool.ResPool)
		self._cms = context.get_instance(CMS)
		self._db = context.get_instance(database.Database)
		
		self._text = self._respool.get_text(model.text_id)
		self._data = json.loads(self._respool.get_text(model.data_id) or '{}')
		self._reason = self._respool.get_text(model.reason)
		self._file = self._respool.get_file(model.file_id)
		self._doc_info = None
	
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
		return uuid.UUID(bytes=self._model.uuid)
	
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
	def filetype(self):
		return self.metadata.get(ArticleMetadataFields.FILETYPE)
	
	@property
	def mimetype(self):
		return self.metadata.get(ArticleMetadataFields.MIMETYPE)
	
	@property
	def view_mode(self):
		return self.metadata.get(ArticleMetadataFields.VIEW_MODE)
	
	@property
	def doc_info(self):
		if self.text and not self._doc_info:
			self._doc_info = restpub.publish_text(self.text,
				math_callback=self._cms._restpub_math_callback,
				internal_callback=self._cms._restpub_internal_callback,
				image_callback=self._cms._restpub_image_callback,
				template_callback=self._cms._restpub_template_callback,
			)
		
		return self._doc_info
	
class ArticleHistoryWriteWrapper(ArticleHistoryReadWrapper):
	def __init__(self, context, model, article_wrapper):
		super(ArticleHistoryWriteWrapper, self).__init__(context, model)
		self._article_wrapper = article_wrapper
	
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
#		if not isinstance(d, datetime.datetime):
#			d = util.datetime_to_naive(iso8601.parse_date(d))
			
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
	
	def save(self):
		assert self._text or self._file
		assert self.view_mode is not None

		article_model = self._article_wrapper._model
		article_model.title = self.metadata.get(ArticleMetadataFields.TITLE) \
			or self.metadata.get(ArticleMetadataFields.FILENAME) \
			or self.text[:160]
		article_model.date = self.publish_date \
			or article_model.date \
			or datetime.datetime.utcnow()
		article_model.view_mode = self.metadata.get(ArticleMetadataFields.VIEW_MODE)
		article_model.version = self._model.version
		
		if not article_model.primary_address and self.addresses:
			article_model.primary_address = tuple(self.addresses)[0]
		
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
			path = self._respool.get_filename(self._model.file_id)
			self.metadata[ArticleMetadataFields.MIMETYPE] = \
				util.magic_cookie_mime.file(path)
			self.metadata[ArticleMetadataFields.FILETYPE] = \
				util.magic_cookie.file(path)
		
		if self._data:
			self._model.data_id = self._respool.set_text(
				json.dumps(self._data), create=True)
		
		query = self._db.session.query(self._db.models.CMSAddress)
		
		if self.addresses:
			# If this condition is removed, then contradictions may occur
			query = query.filter(~self._db.models.CMSAddress.name.in_(self.addresses))
			
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
		
		query = self._db.session.query(self._db.models.CMSArticleTree) \
			.filter_by(article_id=self._model.article_id)
		
		if parent_article_ids:
			# If this this condition is removed, contradictions may occur
			query = query.filter(~self._db.models.CMSArticleTree.parent_article_id.in_(
				parent_article_ids))
		
		for tree_model in query:
			tree_model.parent = None
			self._db.session.delete(tree_model)
		
		query = self._db.session.query(self._db.models.CMSArticleTree) \
			.filter_by(article_id=self._model.article_id)
		
		parent_ids_to_insert = parent_article_ids \
			- frozenset([model.parent_article_id for model in query])
		
		for article_id in parent_ids_to_insert:
#			parent_tree_model = self._db.session.query(
#				self._db.models.CMSArticleTree) \
#				.filter_by(article_id=article_id).first()
#			
#			if not parent_tree_model:
#				parent_tree_model = self._db.models.CMSArticleTree()
#				parent_tree_model.parent_article_id = 0
#				parent_tree_model.article_id = article_id
#				self._db.session.add(parent_tree_model)
##				parent_tree_model.parent = None
			
			new_tree_model = self._db.models.CMSArticleTree()
			new_tree_model.article_id = self._model.article_id
			new_tree_model.parent_article_id = article_id
			self._db.session.add(new_tree_model)
#			new_tree_model.parent = parent_tree_model
		
		acc = self._context.get_instance(accounts.Accounts)
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
		

	
	