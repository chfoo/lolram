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
from tornado.web import HTTPError
from torwuf.web.models.cms import ArticleCollection, TagCountCollection, \
	TagCollection
from torwuf.web.resource import make_map_tags_code, make_reduce_tags_code
from torwuf.web.utils import tag_list_to_str, bytes_to_b32low_str, \
	b32low_str_to_bytes
import base64
import bson.objectid
import datetime
import hashlib
import http.client
import iso8601
import logging
import lolram.utils.restpub
import os.path
import pymongo
import shlex
import tempfile
import torwuf.web.controllers.base
import uuid

_logger = logging.getLogger(__name__)

class CMSController(torwuf.web.controllers.base.BaseController):
	@property
	def article_collection(self):
		return self.application.database[ArticleCollection.COLLECTION]
	
	@property
	def tag_collection(self):
		return self.application.database[TagCollection.COLLECTION]
	
	def init(self):
		self.add_url_spec(r'/a/([0-9a-zA-Z]+)', UniqueItemHandler)
		self.add_url_spec(r'/a/([0-9a-zA-Z]+);([0-9a-zA-Z]+)', ItemFormatHandler)
		self.add_url_spec(r'/cms/article/new', NewArticleHandler)
		self.add_url_spec(r'/cms/article/edit/([0-9a-f]+)', EditArticleHandler)
		self.add_url_spec(r'/cms/article/delete/([0-9a-f]+)', DeleteArticleHandler)
		self.add_url_spec(r'/cms/file/upload', UploadFileHandler)
		self.add_url_spec(r'/cms/file/edit/([0-9a-f]+)', EditFileHandler)
		self.add_url_spec(r'/cms/tags', AllTagsHandler)
		self.add_url_spec(r'/cms/tag/(.*)', TagHandler)
		self.add_url_spec(r'/cms/articles', AllArticlesHandler)
		
		self.article_collection.ensure_index(
			[(ArticleCollection.TAGS, pymongo.ASCENDING)])
		self.article_collection.ensure_index(
			[(ArticleCollection.RELATED_TAGS, pymongo.ASCENDING)])
		self.article_collection.ensure_index(
			[(ArticleCollection.UUID, pymongo.ASCENDING)], unique=True)
	
	def render_text(self, text):
		doc_info = lolram.utils.restpub.publish_text(text)
		
		return doc_info
	
	def generate_tag_count_collection(self):
		self.article_collection.map_reduce(make_map_tags_code(), 
			make_reduce_tags_code(), 
			out=TagCountCollection.COLLECTION)
		
		results = self.application.database[TagCountCollection.COLLECTION].find()
		
		for result in results:
			self.update_tag_count(result['_id'], 
				result[TagCountCollection.COUNT])
		
	def update_tag_count(self, tag_id, count, increment=False):
		if increment:
			self.tag_collection.update({'_id': tag_id}, 
				{'$inc': {TagCollection.COUNT: count}}
			)
		else:
			self.tag_collection.update({'_id': tag_id}, 
				{'$set': {TagCollection.COUNT: count}}
			)


class HandlerMixin(object):
	@property
	def article_collection(self):
		return self.app_controller.database[ArticleCollection.COLLECTION]
	
	@property
	def tag_collection(self):
		return self.app_controller.database[TagCollection.COLLECTION]
	
	def get_disk_file_path(self, hash_str):
		hash_str = hash_str.lower()
		return os.path.join(self.app_controller.config.upload_path, 'cms', hash_str[0:2],
			hash_str[2:4], hash_str[4:6], hash_str)


class UniqueItemHandler(torwuf.web.controllers.base.BaseHandler, HandlerMixin):
	name = 'cms_unique_item'
	
	def get(self, b32_str, params=None):
		uuid_obj = uuid.UUID(bytes=b32low_str_to_bytes(b32_str))
		result = self.article_collection.find_one({ArticleCollection.UUID: uuid_obj})
		
		if result and params == 'download':
			if ArticleCollection.FILE_SHA1 in result:
				self.do_file_download(result)
			else:
				self.set_header('Content-Type', 'text/plain; encoding=utf-8')
				self.write(result[ArticleCollection.TEXT])
				self.finish()
				return
		
		if result and ArticleCollection.FILE_SHA1 not in result:
			self.do_article(result)
		elif result:
			self.do_file(result)
		else:
			raise HTTPError(http.client.NOT_FOUND)
	
	def do_article(self, result):
		rest_doc = self.controller.render_text(result[ArticleCollection.TEXT])
		query = {
			ArticleCollection.TAGS: result[ArticleCollection.RELATED_TAGS],
			ArticleCollection.FILE_SHA1: {'$exists': True},
		}
		related_files = list(self.article_collection.find(query,
			sort=[(ArticleCollection.PUBLICATION_DATE, pymongo.ASCENDING)]
		))
		
		self.render('cms/view_article.html', article=result, 
			rest_doc=rest_doc,
			related_files=related_files,
			ArticleCollection=ArticleCollection)
	
	def do_file(self, result):
		query = {
			ArticleCollection.TAGS: result[ArticleCollection.TAGS],
			ArticleCollection.FILE_SHA1: {'$exists': False},
		}
		related_articles = list(self.article_collection.find(query,
			sort=[(ArticleCollection.PUBLICATION_DATE, pymongo.ASCENDING)]
		))
		
		query = {
			ArticleCollection.TAGS: result[ArticleCollection.TAGS],
			ArticleCollection.FILE_SHA1: {'$exists': True},
		}
		related_files = list(self.article_collection.find(query,
			sort=[(ArticleCollection.PUBLICATION_DATE, pymongo.ASCENDING)]
		))
		
		prev_article, next_article = self.find_prev_and_next(result[ArticleCollection.UUID], related_files)
		
		self.render('cms/view_file.html', article=result, 
			related_articles=related_articles,
			prev_article=prev_article,
			next_article=next_article,
			ArticleCollection=ArticleCollection)
	
	def find_prev_and_next(self, target_uuid_obj, related_articles):
		related_uuids = [article[ArticleCollection.UUID] for article in related_articles]
		
		index = related_uuids.index(target_uuid_obj)
		
		if index > 0:
			prev_index = index - 1
			prev_article = related_articles[prev_index]
		else:
			prev_article = None
		
		if index < len(related_uuids) - 1:
			next_index = index + 1
			next_article = related_articles[next_index]
		else:
			next_article = None
		
		
		return (prev_article, next_article)
	
	def do_file_download(self, result, ):
		self.redirect(self.static_url(self.get_disk_file_path(
			base64.b16encode(result[ArticleCollection.FILE_SHA1]).decode())))

class ItemFormatHandler(UniqueItemHandler):
	name = 'cms_item_format'
	
	def get(self, b32_str, params):
		UniqueItemHandler.get(self, b32_str, params)

class BaseEditArticleHandler(torwuf.web.controllers.base.BaseHandler, HandlerMixin):
	def new_form_data(self):
		return dict(
			uuid=uuid.uuid4(),
			date=datetime.datetime.utcnow(),
			title='',
			tags='',
			text='',
			related_tags='',
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
				related_tags=tag_list_to_str(result[ArticleCollection.RELATED_TAGS]),
			)
		
	def save(self, object_id=None):
		uuid_obj = uuid.UUID(self.get_argument('uuid'))
		title = self.get_argument('title', None)
		text = self.get_argument('text', None)
		# TODO: remove duplicates with sets
		tags = shlex.split(self.get_argument('tags', ''))
		related_tags = shlex.split(self.get_argument('related_tags', ''))
			
		rest_doc = self.controller.render_text(text)
		
		if not title and rest_doc.title:
			self.add_message('Title automatically parsed from document')
			
			title = rest_doc.title
		
		publication_date = None
		
		if not self.get_argument('date', None) and rest_doc.meta.get('date'):
			try:
				publication_date = iso8601.parse_date(rest_doc.meta['date'])
				
				self.add_message('Date automatically parsed from document')
			except iso8601.ParseError:
				pass
		
		if not publication_date and self.get_argument('date', None):
			publication_date = iso8601.parse_date(self.get_argument('date'))
		elif not publication_date:
			publication_date = datetime.datetime.utcnow()
		
		form_data = dict(
			uuid=uuid_obj,
			date=publication_date,
			title=title,
			tags=tag_list_to_str(tags),
			text=text,
			rest_doc=rest_doc,
			related_tags=tag_list_to_str(related_tags),
		)
		
		if self.get_argument('save', False) != False:
			d = {
				ArticleCollection.PUBLICATION_DATE: publication_date,
				ArticleCollection.TAGS: tags,
				ArticleCollection.TITLE: title,
				ArticleCollection.TEXT: text,
				ArticleCollection.UUID: uuid_obj,
				ArticleCollection.RELATED_TAGS: related_tags,
			}
			
			if object_id:
				d['_id'] = object_id
				self.article_collection.save(d)
			else:
				object_id = self.article_collection.insert(d)
			
			# TODO: just update the tag counts here
			self.controller.generate_tag_count_collection()
			
			self.add_message('Article saved')
			
			id_str = bytes_to_b32low_str(uuid_obj.bytes)
			self.redirect(self.reverse_url(UniqueItemHandler.name, id_str),
				status=http.client.SEE_OTHER, api_data={
					'id': object_id,
					'uuid': uuid_obj,
				})
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


class DeleteArticleHandler(torwuf.web.controllers.base.BaseHandler, HandlerMixin):
	name = 'cms_article_delete'
	
	def get(self, hex_id):
		object_id = bson.objectid.ObjectId(hex_id)
		result = self.article_collection.find_one({'_id': object_id})
		
		if result:
			self.render('cms/delete_article', 
				title=result[ArticleCollection.TITLE],
				confirm_key=self.generate_confirm_key(object_id))
		else:
			raise HTTPError(http.client.NOT_FOUND)
	
	def post(self, hex_id):
		object_id = bson.objectid.ObjectId(hex_id)
		result = self.article_collection.find_one({'_id': object_id})
		confirmed = self.get_argument('confirm', False) is not False
		
		if result and confirmed:
			self.article_collection.remove({'_id': object_id})
			self.add_message('Article deleted')
			self.redirect('/', api_data={})
		elif result:
			HTTPError(http.client.BAD_REQUEST, 'bad confirm key')
		else:
			raise HTTPError(http.client.NOT_FOUND)


class BaseEditFileHandler(torwuf.web.controllers.base.BaseHandler, HandlerMixin):
	def save_to_disk(self, file_obj):
		with tempfile.TemporaryDirectory() as dir_path:
			dest_temp_path = os.path.join(dir_path, 'file')
			dest_file = open(dest_temp_path, 'wb')
			hash_obj = hashlib.sha1()
			
			while True:
				data = file_obj.read(4096)
				
				if data == b'':
					break
				
				hash_obj.update(data)
				dest_file.write(data)
			
			dest_path = self.get_disk_file_path(hash_obj.hexdigest())
			
			if not os.path.exists(dest_path):
				os.makedirs(os.path.dirname(dest_path))
				os.rename(dest_temp_path, dest_path)
			
		return hash_obj.digest()
	
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
		
		title = self.get_argument('title', None)
		text = self.get_argument('text', None)
		publication_date = iso8601.parse_date(self.get_argument('date', None))
		tags = shlex.split(self.get_argument('tags', ''))
		uuid_obj = uuid.UUID(self.get_argument('uuid'))
		
		
		if object_id is None:
			file_obj = self.request.field_storage['file'].file
			filename = self.request.field_storage['file'].name
			sha1 = self.save_to_disk(file_obj)
		
			object_id = self.article_collection.insert({
				ArticleCollection.FILENAME: filename,
				ArticleCollection.PUBLICATION_DATE: publication_date,
				ArticleCollection.FILE_SHA1: sha1,
				ArticleCollection.TAGS: tags,
				ArticleCollection.TEXT: text,
				ArticleCollection.TITLE: title,
				ArticleCollection.UUID: uuid_obj,
			})
		else:
			update_dict = {
				ArticleCollection.PUBLICATION_DATE: publication_date,
				ArticleCollection.TAGS: tags,
				ArticleCollection.TEXT: text,
				ArticleCollection.TITLE: title,
				ArticleCollection.UUID: uuid_obj,
			}
			
			if 'file' in self.request.field_storage:
				file_obj = self.request.field_storage['file'].file
				filename = self.request.field_storage['file'].name
				sha1 = self.save_to_disk(file_obj)
				
				update_dict[ArticleCollection.FILENAME] = filename
				update_dict[ArticleCollection.FILE_SHA1] = sha1
				
				self.article_collection.update({'_id': object_id},
					update_dict
				)
		
		self.add_message('File saved')
		self.redirect(self.reverse_url(UniqueItemHandler.name, 
			bytes_to_b32low_str(uuid_obj.bytes)))


class UploadFileHandler(BaseEditFileHandler):
	name = 'cms_file_upload'
	
	def get(self):
		self.render('cms/upload_file.html', **self.new_form_data())
	
	def post(self):
		self.save()


class EditFileHandler(BaseEditFileHandler):
	name = 'cms_file_edit'
	
	def get(self, hex_id):
		form_data = self.get_form_data(hex_id)
		
		if form_data:
			self.render('cms/upload_file.html', **form_data)
		else:
			raise HTTPError(http.client.NOT_FOUND)
	
	def post(self, hex_id):
		object_id = bson.objectid.ObjectId(hex_id)
		self.save(object_id)


class AllTagsHandler(torwuf.web.controllers.base.BaseHandler, HandlerMixin):
	name = 'cms_all_tags'
	
	def get(self):
		results = list(self.tag_collection.find(sort=[(TagCollection.TITLE, pymongo.ASCENDING)]))
		
		self.render('cms/all_tags.html', TagCollection=TagCollection, 
			tags=results,
		)

class TagHandler(torwuf.web.controllers.base.BaseHandler, HandlerMixin):
	name = 'cms_tag'
	
	def get(self, tag_id):
		query = {
			ArticleCollection.TAGS: tag_id,
		}
		results = list(self.article_collection.find(query,
			sort=[(ArticleCollection.TITLE, pymongo.ASCENDING)]))
		
		self.render('cms/all_articles.html', ArticleCollection=ArticleCollection, 
			articles=results,
		)	
		
class AllArticlesHandler(torwuf.web.controllers.base.BaseHandler, HandlerMixin):
	name = 'cms_all_articles'
	
	def get(self):
		results = list(self.article_collection.find(
			sort=[(ArticleCollection.TITLE, pymongo.ASCENDING)]))
		
		self.render('cms/all_articles.html', ArticleCollection=ArticleCollection, 
			articles=results,
		)	