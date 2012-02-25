'''Content management system controller (blog, articles, files, etc)'''
#
#	Copyright (c) 2012 Christopher Foo <chris.foo@gmail.com>
#
#	This file is part of Torwuf.
#
#	Torwuf is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	Torwuf is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with Torwuf.  If not, see <http://www.gnu.org/licenses/>.
#
from torwuf.web.models.cms import ArticleCollection, FileCollection
from torwuf.web.utils import tag_list_to_str, bytes_to_b32low_str
import bson.objectid
import datetime
import iso8601
import logging
import lolram.utils.restpub
import shlex
import torwuf.web.controllers.base
import uuid

_logger = logging.getLogger(__name__)

class CMSController(torwuf.web.controllers.base.BaseController):
	def init(self):
		self.add_url_spec(r'/a/([0-9a-zA-Z]+)', UniqueItemHandler)
		self.add_url_spec(r'/cms/article/new', NewArticleHandler)
		self.add_url_spec(r'/cms/article/edit/([0-9a-f]+)', EditArticleHandler)
		self.add_url_spec(r'/cms/article/delete/([0-9a-f]+)', DeleteArticleHandler)
		self.add_url_spec(r'/cms/file/upload', UploadFileHandler)
		self.add_url_spec(r'/cms/file/edit/([0-9a-f]+)', EditFileHandler)
		self.add_url_spec(r'/cms/file/delete/([0-9a-f]+)', DeleteFileHandler)
	
	def render_text(self, text):
		doc_info = lolram.utils.restpub.publish_text(text)
		
		return doc_info

class HandlerMixin(object):
	@property
	def article_collection(self):
		return self.app_controller.database[ArticleCollection.COLLECTION]
	
	@property
	def file_collection(self):
		return self.app_controller.database[FileCollection.COLLECTION]

class UniqueItemHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'cms_unique_item'

class BaseEditArticleHandler(torwuf.web.controllers.base.BaseHandler, HandlerMixin):
	def new_form_data(self):
		return dict(
			uuid=uuid.uuid4(),
			date=datetime.datetime.utcnow(),
			title='',
			tags='',
			text='',
		)
	
	def get_form_data(self, hex_id):
		object_id = bson.objectid.ObjectId(hex_id)
		
		result = self.article_collection.find_one({'_id': object_id})
		
		if result:
			return dict(
				uuid=result[ArticleCollection.UUID],
				date=result[ArticleCollection.PUBLICATION_DATE],
				title=result[ArticleCollection.TITLE],
				tags=tag_list_to_str(result[ArticleCollection.TAGS]),
				text=result[ArticleCollection.TEXT],
			)
		
	def save(self, object_id=None):
		uuid_obj = uuid.UUID(self.get_argument('uuid'))
		title = self.get_argument('title', '')
		text = self.get_argument('text', '')
		tags = shlex.split(self.get_argument('tags', ''))
			
		doc_info = self.controller.render_text(text)
		
		if not title and doc_info.title:
			title = doc_info.title
		
		publication_date = None
		
		if not self.get_argument('date', None) and doc_info.meta.get('date'):
			try:
				publication_date = iso8601.parse_date(doc_info.meta['date'])
			except iso8601.ParseError:
				pass
		
		if self.get_argument('date', None):
			publication_date = iso8601.parse_date(self.get_argument('date'))
		else:
			publication_date = datetime.datetime.utcnow()
		
		form_data = dict(
			uuid=uuid_obj,
			date=publication_date,
			title=title,
			tags=tag_list_to_str(tags),
			text=text,
			doc_info=doc_info
		)
		
		if 'save' in self.request.field_storage:
			d = {
				ArticleCollection.PUBLICATION_DATE: publication_date,
				ArticleCollection.TAGS: tags,
				ArticleCollection.TITLE: title,
				ArticleCollection.TEXT: text,
				ArticleCollection.UUID: uuid_obj,
			}
			
			if object_id:
				d['_id'] = object_id
				self.article_collection.save(d)
			else:
				object_id = self.article_collection.insert(d)
			
			self.add_message('Article saved')
			
			id_str = bytes_to_b32low_str(object_id.binary)
			self.redirect(self.reverse_url(UniqueItemHandler.name, id_str))
		else:
			self.render('cms/edit_article.html', **form_data)

class NewArticleHandler(BaseEditArticleHandler):
	name = 'cms_article_new'
	
	def get(self):
		form_data = self.new_form_data()
		
		self.render('cms/edit_article.html', **form_data)
	
	def post(self):
		self.save()

class EditArticleHandler(BaseEditArticleHandler):
	name = 'cms_article_edit'

	def get(self, hex_id):
		form_data = self.get_form_data(hex_id)
		
		self.render('cms/edit_article.html', **form_data)
	
	def post(self, hex_id):
		object_id = bson.objectid.ObjectId(hex_id)
		self.save(object_id)


class DeleteArticleHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'cms_article_delete'
	

class UploadFileHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'cms_file_upload'


class EditFileHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'cms_file_edit'

class DeleteFileHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'cms_delete_file'
	
