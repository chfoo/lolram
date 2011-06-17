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
	TURING_TEST_PASSED = 2
	COMMENTER = 3
	WRITER = 4
	MODERATOR = 5
	CURATOR = 6
	BUREAUCRAT = 7
	BOT = 8

class ArticleViewModes(object):
	ARTICLE = 1
	COMMENT = 2
	FILE = 3
	THREAD = 4

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
	
	def init(self):
		db = self.context.get_instance(database.Database)
		db.add(CMSArticlesMeta)
		db.add(CMSArticleTreeMeta)
		db.add(CMSHistoryMeta)
		db.add(CMSAddressesMeta)
		
		restpub.template_callback = self._restpub_template_callback
	
	def _restpub_template_callback(self, name):
		article = self.get_article(address=name)
		
		if article:
			return article.current.text
		
		article = self.get_article(uuid=uuid.UUID(name).bytes)
		
		if article:
			return article.current.text
	
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
				self.context.response.ok()
				self._build_article_page(article.current)
				
		elif arg1 == self.GET and arg2:
			uuid_bytes = util.b32low_to_bytes(arg2)
			article = self.get_article(uuid=uuid_bytes)
			
			if article:
				self.context.response.ok()
				self._build_article_page(article)
		
		elif arg1 == self.GET_VERSION and arg2:
			uuid_bytes = util.b32low_to_bytes(arg2)
			article = self.get_article_history(uuid=uuid_bytes)
			
			if article:
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
			else:
				article = self.new_article()
				article_version = article.edit()
			
			self.context.response.ok()
			
			if arg1 == self.EDIT:
				self._build_article_preview(article_version)
				self._build_article_edit_page(article_version)
			else:
				self._build_upload_page(article_version)
		
		elif arg1 == self.RAW and arg2:
			uuid_bytes = util.b32low_to_bytes(arg2)
			article = self.get_article_history(uuid=uuid_bytes)
			
			if article:
				self.context.response.ok()
				return self._serve_raw(article)
		
		elif arg1 == self.EDIT_VIEW and arg2:
			uuid_bytes = util.b32low_to_bytes(arg2)
			article = self.get_article(uuid=uuid_bytes)
			article_version = article.edit()
			
			self.context.response.ok()
			self._build_article_edit_view_page(article_version)
	
	def _build_article_page(self, article):
		self._doc.title = article.title
		self._doc.append(dataobject.MVPair(article))
	
	def _build_article_version(self, article_history):
		self._doc.title = u'Viewing past version: %s' % article_history.title
		self._doc.append(dataobject.MVPair(article_history))
	
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
		for info in articles:
			table.rows.append((
				(info.title, self.context.str_url(fill_controller=True,
					args=(util.bytes_to_b32low(info.uuid),))), 
				str(info.date), 
			))
			
			counter += 1
			if counter > 50:
				page_info.more = True
				break
		
		self._doc.append(dataobject.MVPair(page_info, views.PagerView))
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
				args=(self.GET_VERSION, util.bytes_to_b32low(info.uuid)))
			
			table.rows.append((
				str(info.version), 
				str(info.created), 
				(info.title or info.upload_filename or '(untitled)', url),
			))
					
			counter += 1
			if count > 50:
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
		
		
		
		if not self._acc.is_authorized(ActionRole.NAMESPACE, ActionRole.WRITER) and False:
			self._doc.add_message('Sorry, you cannot upload files', 
				'You do not have the permissions necessary to upload files')
			
			return
		
		if 'submit-publish' in self.context.request.form:
			filename = self.context.request.form.getfirst('filename') \
				or self.context.request.form['file'].filename
			article_version.upload_filename = filename
			article_version.file = self.context.request.form['file'].file
			article_version.reason = self.context.request.form.getfirst('reason')
			
			if not article_version.addresses:
				article_version.addresses = article_version.addresses | \
					frozenset([filename])
			
			assert filename
			
			article_version.save()
			
			self._doc.add_message('Upload was a success')
			
			return
		
		self._doc.add_message('Please name your file uniquely and carefully')
		
		form.textbox('filename', 'Filename (optional):')
		form.textbox('file', 'File:', validation=form.Textbox.FILE, required=True)
		form.textbox('reason', 'Reason or changes:')
		form.button('submit-publish', 'Upload')
		
		self._doc.append(dataobject.MVPair(form))
		
	
	def _build_article_edit_page(self, article_version):
		form = models.Form(models.Form.POST, 
			self.context.str_url(fill_path=True, 
				fill_args=True, fill_params=True, fill_query=True))
		
	
	def _build_edit_form(self, article_history=None, type='article',
	allow_metadata=True, allow_reason=True):
		
		addresses = None
		date = None
		parents = None
		text = None
		reason = None
		title = None
		
		if article and 'addresses' not in self.context.request.form:
			addresses = u'/'.join(article.addresses)
		
		if 'date' not in self.context.request.form:
			if article:
				date = str(article.date)
#			else:
#				date = str(datetime.datetime.utcnow())
	
		if 'title' not in self.context.request.form:
			if article:
				title = article.title
		
		if 'parents' not in self.context.request.form and article:
			parents = ' '.join((s.encode('hex') for s in article.parents))
		
		if 'text' not in self.context.request.form and article and type == 'article':
			text = article.text
		
		form.textbox('uuid', article.uuid.encode('hex') if article else '',
			validation=form.HIDDEN)
		
		if allow_metadata:
			form.textbox('title', u'Title (Leave blank for automatic generation):',
				title)
			form.textbox('date', 'Publish date (Leave blank for automatic generation):', 
				date,)
		
		if type == 'article':
			form.textbox('text', 'Article content:', text, large=True, required=True)
		else:
			form.textbox('file', 'File', validation=Form.FILE, required=True)
		
		if allow_metadata:
			form.textbox('addresses', 
				u'Addresses (Use the slash symbol / as a deliminator):', 
				addresses)
			form.textbox('parents', 'Parent UUIDs:', parents)
		
		if allow_reason:
			form.textbox('reason', 'Reason for edit:', reason)
		
		form.button('submit-publish', 'Publish')
		
		if type == 'article':
			form.button('submit-preview', 'Preview')
		
		return dataobject.MVPair(form)
		
	def _process_edit_form(self, save=False, type='article', allow_metadata=True):
		cms = self.context.get_instance(CMS)
		uuid = self.context.request.form.getfirst('uuid')
		addresses = self.context.request.form.getfirst('addresses', '').decode('utf8')
		date = self.context.request.form.getfirst('date')
		title = self.context.request.form.getfirst('title', '').decode('utf8')
		parents = self.context.request.form.getfirst('parents')
		reason = self.context.request.form.getfirst('reason', '').decode('utf8')
		text = self.context.request.form.getfirst('text', '').decode('utf8')
		
		if save and uuid:
			article = cms.get_article(uuid=uuid.decode('hex'))
			
			if not article:
				raise Exception('Article not found')
		else:
			article = cms.new_article()
		
		if type == 'article':
			article.text = text
			doc_info = article.parse_text()
			
			if date and allow_metadata:
				article.date = iso8601.parse_date(date)
			elif 'date' in doc_info.meta and allow_metadata:
				article.date = iso8601.parse_date(doc_info.meta['date'])
			else:
				article.date = datetime.datetime.utcnow()
			
			# XXX Make it naive in UTC
			t = article.date.utctimetuple()
			article.date = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec, article.date.microsecond)
			
			if title and allow_metadata:
				article.title = title
			elif doc_info.title:
				article.title = doc_info.title
			else:
				article.title = text.lstrip().splitlines()[0][:160]
		
		if addresses and allow_metadata:
			article.addresses = frozenset(addresses.split(u'/'))
		
		if parents and allow_metadata:
			uuid_list = parents.split()
			l = []
			
			for s in uuid_list:
				a = cms.get_article(uuid=s.decode('hex'))
				
				if not a:
					raise Exception('Parent does not exist')
				
				l.append(a)
			
			article.parents = frozenset(l)
		
		if type == 'upload':
			f = self.context.request.form['file']
			
			article.set_file(file_obj=f.file, upload_filename=f.filename)
		
		if save:
			article.save(reason)
		
		return article


class ArticleView(dataobject.BaseView):
	PLAIN_TEXT = 'plain'
	RESTRUCTUREDTEXT = 'rest'
	
	ARTICLE_FORMAT_PREVIEW = 'preview'
	
	@classmethod
	def to_html(cls, context, model, article_format='full'):
		element = lxmlbuilder.E.article(CLASS='article')
		
		if article_format in ('full', 'history'):
			author_name = u'(unknown)'
			
			if model._model.account and model._model.account.nickname:
				author_name = model._model.account.nickname
			
			if article_format == 'history':
				date = model.created
			else:
				date = model.publish_date or model.date
			
			e = lxmlbuilder.E.aside(
				lxmlbuilder.SPAN(u'(%s)' % date, CLASS='articleInfoDate'),
				lxmlbuilder.SPAN(author_name, CLASS='articleInfoAuthor'),
				CLASS='articleInfo')
			
			if article_format == 'history':
				e.append(lxmlbuilder.SPAN(u'Version %s' % model.version_number,
					CLASS='articleInfoVersion'))
			
			element.append(e)
		
		if model.text:
			doc_info = model.doc_info
			assert doc_info
			
			meta_table = lxmlbuilder.TABLE()
			
			for n, v in doc_info.meta.iteritems():
				tr = lxmlbuilder.TR(
					lxmlbuilder.TH(n), lxmlbuilder.TD(v)
				)
				meta_table.append(tr)
			
			element.append(meta_table)
			
			if doc_info.errors:
				e = lxmlbuilder.PRE(model.text)
			else:
				e = lxml.html.fromstring(doc_info.html_parts['fragment'] or '<div></div>')
			
			element.append(e)
		
		elif model.file:
			url = context.str_url(fill_controller=True, 
				args=[CMS.RAW, util.bytes_to_b32low(model.uuid.bytes)])
			
			element.append(lxmlbuilder.IMG(src=url)) 
		
		ul = lxmlbuilder.UL(CLASS='articleActions')
		
		def add(label, url):
			ul.append(lxmlbuilder.LI(lxmlbuilder.A(label, href=url)))
		
		if article_format in ('full', 'history'):
			add('Raw', context.str_url(
				args=('raw', util.bytes_to_b32low(model.uuid.bytes)),
				fill_controller=True,
			))
		
		if article_format == 'full':
			add('Edit', context.str_url(
				args=('edit', util.bytes_to_b32low(model.uuid.bytes),),
				fill_controller=True,
			))
			add('History', context.str_url(
				args=('history', util.bytes_to_b32low(model.uuid.bytes),),
				fill_controller=True,
			))
			add('Reply', context.str_url(
				args=('reply', util.bytes_to_b32low(model.uuid.bytes),),
				fill_controller=True,
			))
		elif article_format == 'history':
			add(u'View current version', context.str_url(
				args=(util.bytes_to_b32low(model.current_article.uuid),),
				fill_controller=True,
			))
		
		element.append(ul)
		
		return element

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
		
		if o and not isinstance(o, datatime.datetime):
			return iso8601.parse_date(o)
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
		return ArticleWrapper(self._context, 
			self._cms.get_article(id=self._model.article_id))
	
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
		assert self.text is not None
		
		if not self._doc_info:
			self._doc_info = restpub.publish_text(self.text)
		
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
		if not isinstance(d, datetime.datetime):
			d = iso8601.parse_date(d)
			
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
		article_model = self._article_wrapper._model
		article_model.title = self.metadata.get(ArticleMetadataFields.TITLE) \
			or self.metadata.get(ArticleMetadataFields.FILENAME)
		article_model.date = self.metadata.get(ArticleMetadataFields.PUBLISH_DATE)
		article_model.view_mode = self.metadata.get(ArticleMetadataFields.VIEW_MODE)
		article_model.version = self._model.version
		
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
			# TODO save filetype, mimetype
		
		assert self._text or self._file
		
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
		

	
	