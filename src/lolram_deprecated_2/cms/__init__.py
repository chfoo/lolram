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

import abc
import uuid
import datetime

import iso8601



class ArticleViewModes(object):
	NORMAL = 0
	CATEGORY = 1
	GALLERY = 2


class Article(object):
	def __init__(self):
		self.uuid = None
		self.current_version_number = None
		self.title = None
		self.publication_date = None
		self.author_account_id = None
		self.view_mode = None


class ArticleVersion(object):
	def __init__(self):
		self.uuid = None
		self.article_uuid = None
		self.version_number = None
		self.title = None
		self.publication_date = None
		self.creation_date = None
		self.text = None
		self.file = None
		self.editable_by_others = None
		self.editor_account_id = None
		self.parent_article_uuids = None
		self.addresses = None
		self.allow_children = None
		self.reason = None
		self.filename = None
		self.view_mode = None

class Manager(object):
	__metaclass__ = abc.ABCMeta
	
	FILTER_IS_FILE = 'file'
	FILTER_IS_TEXT = 'text'
	SORT_DATE = 'date'
	SORT_TITLE = 'title'
	
	def set_text_resource_pool(self, text_pool):
		self._text_pool = text_pool
		
	def set_file_resource_pool(self, file_pool):
		self._file_pool = file_pool
	
	@abc.abstractmethod
	def get_article(self, article_uuid):
		'''Get an article
		
		:parameters:
			article_uuid : `uuid.UUID`
				The article UUID
		
		:rtype: `Article`
		'''
		
		raise NotImplementedError()
	
	@abc.abstractmethod
	def look_up_address(self, address):
		'''Get article UUID associated with given address
		
		:parameters:
			address : `unicode`
				The address
		
		:rtype: `uuid.UUID`
		'''
		
		raise NotImplementedError()
	
	@abc.abstractmethod
	def get_article_version(self, article_version_uuid=None, article_uuid=None,
	article_version_number=None):
		'''Get an article version
		
		:parameters:
			article_version_uuid : `uuid.UUID`
				The article version's UUID
			article_uuid : `uuid.UUID`
				The article UUID. This parameter is used with the 
				``article_version_number`` parameter.
			article_version_number : `int` or `long` or `None`
				The revision number of article version. The number begins
				with 1 and increments. If ``article_uuid`` is provided and
				``article_version_number`` is `None`, then return the largest
				revision number.
		
		:rtype: `ArticleVersion`
		'''
		
		raise NotImplementedError()
	
	@abc.abstractmethod
	def save_article_version(self, article_version):
		'''Save the article version to the persistent storage
		
		:parameters:
			article_version : `ArticleVersion`
		
		'''
		
		raise NotImplementedError()
	
	@abc.abstractmethod
	def browse_articles(self, offset=0, limit=50, filter=None, 
	sort=SORT_TITLE, descending=False, parent_uuid=None, descendants=None):
		'''Get list of articles
		
		:rtype: `list`
		:return: A `list` of `Article`
		'''
	
		raise NotImplementedError()
	
	@abc.abstractmethod
	def browse_article_versions(self, offset=0, limit=50, filter=None,
	sort=SORT_DATE, descending=True):
		'''Get list of article versions
		
		:rtype: `list`
		:return: A `list` of `ArticleVersion`
		'''
	
		raise NotImplementedError()
	
	def new_article_version(self, article_uuid=None):
		'''Return a new article version for editing
		
		:parameters:
			article_uuid : `uuid.UUID`
				The UUID of the article to edit. Use `None` to edit a completely
				new article 
		
		:rtype: `ArticleVersion`
		'''
		
		article_version = ArticleVersion()
		article_version.uuid = uuid.uuid4()
		article_version.creation_date = datetime.datetime.utcnow().replace(tzinfo=iso8601.iso8601.Utc())
		
		if article_uuid:
			prev_version = self.get_article_version(article_uuid=article_uuid)
			article_version.article_uuid = article_uuid
			article_version.version_number = prev_version.version_number + 1 # approximately
			article_version.title = prev_version.title
			article_version.publication_date = prev_version.publication_date
			article_version.text = prev_version.text
			article_version.editable_by_others = prev_version.editable_by_others
			article_version.parent_article_uuids = prev_version.parent_article_uuids
			article_version.addresses = prev_version.addresses
			article_version.allow_children = prev_version.allow_children
			article_version.view_mode = prev_version.view_mode
			
		else:
			article_version.version_number = 1
			article_version.publication_date = article_version.creation_date
			article_version.editable_by_others = False
			article_version.parent_article_uuids = []
			article_version.addresses = []
			article_version.allow_children = True
		
		return article_version
	
	@abc.abstractmethod
	def import_articles(self, file_obj):
		raise NotImplementedError()
	
	@abc.abstractmethod
	def export_articles(self, file_obj, articles=None):
		raise NotImplementedError()
