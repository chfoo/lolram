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
import datetime
import iso8601
import logging
import torwuf.web.controllers.base
import uuid
import lolram.utils.restpub

_logger = logging.getLogger(__name__)

class CMSController(torwuf.web.controllers.base.BaseController):
	def init(self):
		self.add_url_spec(r'/a/([0-9a-zA-Z]+)', UniqueItemHandler)
		self.add_url_spec(r'/cms/article/new', NewArticleHandler)
		self.add_url_spec(r'/cms/article/edit/([0-9a-zA-Z]+)', EditArticleHandler)
		self.add_url_spec(r'/cms/article/delete/([0-9a-zA-Z]+)', DeleteArticleHandler)
		self.add_url_spec(r'/cms/file/upload', UploadFileHandler)
		self.add_url_spec(r'/cms/file/edit/([0-9a-zA-Z]+)', EditFileHandler)
		self.add_url_spec(r'/cms/file/delete/([0-9a-zA-Z]+)', DeleteFileHandler)
	
	def render_text(self, text):
		doc_info = lolram.utils.restpub.publish_text(text)
		
		return doc_info

class UniqueItemHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'cms_unique_item'


class NewArticleHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'cms_article_new'
	
	def get(self):
		form_data = dict(
			id=uuid.uuid4(),
			date=datetime.datetime.utcnow(),
		)
		
		self.render('cms/edit_article.html', form_data=form_data)
	
	def post(self):
		form_data = dict(
			id=self.get_argument('id'),
			date=self.get_argument('date', datetime.datetime.utcnow()),
			title=self.get_argument('title', ''),
			tags=self.get_argument('tags', ''),
			related_tags=self.get_argument('related_tags', ''),
			text=self.get_argument('text', '')
		)
		
		text = self.get_argument('text', '')
		doc_info = self.controller.render_text(text)
		
		self.render('cms/edit_article.html', form_data=form_data, doc_info=doc_info)

class EditArticleHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'cms_article_edit'


class DeleteArticleHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'cms_article_delete'
	

class UploadFileHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'cms_file_upload'


class EditFileHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'cms_file_edit'

class DeleteFileHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'cms_delete_file'
	
