# encoding=utf8

'''MongoDB backend'''

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

from lolram_deprecated_2.cms import ArticleViewModes, Manager, Article, \
	ArticleVersion
import cStringIO
import csv
import iso8601
import json
import pymongo
import uuid

csv.field_size_limit(1000000000)

class Keys(object):
	AUTHOR_ACCOUNT_ID = 'auacid'
	CURRENT_VERSION_NUMBER = 'cuvenu'
	PUBLICATION_DATE = 'puda'
	TITLE = 'ti'
	TARGET_UUID = 'tauu'
	VERSION_NUMBER = 'venu'
	ADDRESSES = 'ad'
	ALLOW_CHILDREN = 'alch'
	CREATION_DATE = 'crda'
	EDITABLE_BY_OTHERS = 'edbyot'
	EDITOR_ACCOUNT_ID = 'edacid'
	PARENT_UUID_ARRAY = 'pauuar'
	TEXT_ID = 'teid'
	FILE_ID = 'fiid'
	TITLE_TEXT_ID = 'titeid'
	ANCESTOR_UUID_ARRAY = 'anuuar'
	UUID = 'uu'
	REASON_ID = 'reid'
	FILENAME = 'fi'
	VIEW_MODE = 'vimo'


VIEW_TYPE_MAP = {
	'category': ArticleViewModes.CATEGORY,
	'gallery': ArticleViewModes.GALLERY,
}
			

class ManagerOnMongo(Manager):
	def __init__(self, db, text_res_pool, file_res_pool, 
	col_name_prefix='lr_cms_'):
		self._col_names = dict(
			articles='%sarticles' % col_name_prefix,
			versions='%sarticle_versions' % col_name_prefix,
#			tree='%stree' % col_name_prefix,
#			addresses='%sarticle_addresses' % col_name_prefix,
		)
		
		self._db = db
		self._text_res_pool = text_res_pool
		self._file_res_pool = file_res_pool
		
		self._db[self._col_names['versions']].ensure_index([
			(Keys.TARGET_UUID, pymongo.ASCENDING), 
			(Keys.VERSION_NUMBER, pymongo.ASCENDING),
		])
		
		self._db[self._col_names['articles']].ensure_index([
			(Keys.ANCESTOR_UUID_ARRAY, pymongo.ASCENDING)])
		
		self._db[self._col_names['articles']].ensure_index([
			(Keys.PARENT_UUID_ARRAY, pymongo.ASCENDING)])
		
		self._db[self._col_names['articles']].ensure_index([
			(Keys.ADDRESSES, pymongo.ASCENDING)])
	
	@property
	def collection_names(self):
		return self._col_names
	
	def set_database(self, db):
		self._db = db
	
	def get_article(self, article_uuid):
		assert isinstance(article_uuid, uuid.UUID)
		
		result = self._db[self._col_names['articles']].find_one(
			{'_id':article_uuid})
		
		if result:
			article = self._populate_article(result)
			
			return article
	
	def look_up_address(self, address):
		address = unicode(address)
		
		result = self._db[self._col_names['articles']].find_one(
			{Keys.ADDRESSES: address}
		)
		
		if result:
			return result['_id']
	
	def get_article_version(self, article_version_uuid=None,
	article_uuid=None, article_version_number=None ):
		if article_version_uuid:
			assert isinstance(article_version_uuid, uuid.UUID)
		
			result = self._db[self._col_names['versions']].find_one(
				{'_id': article_version_uuid})
			
			if result:
				return self._populate_article_version(result)
		
		elif article_uuid:
			assert isinstance(article_uuid, uuid.UUID)
			
			if article_version_number:
				result = self._db[self._col_names['versions']].find_one(
					{Keys.TARGET_UUID: article_uuid, 
					Keys.VERSION_NUMBER: article_version_number,
				})
			else:
				result = self._db[self._col_names['versions']].find_one(
					{Keys.TARGET_UUID: article_uuid},
					sort=[(Keys.VERSION_NUMBER, pymongo.DESCENDING)],
				)
			
			if result:
				return self._populate_article_version(result) 
	
	def _populate_article(self, db_document):
		article = Article()
		article.author_account_id = db_document[Keys.AUTHOR_ACCOUNT_ID]
		article.current_version_number = db_document[Keys.CURRENT_VERSION_NUMBER]
		article.publication_date = db_document[Keys.PUBLICATION_DATE]
		article.title =  db_document[Keys.TITLE]
		article.uuid = db_document['_id']
		article.view_mode = db_document.get(Keys.VIEW_MODE)
		
		return article
	
	def _populate_article_version(self, db_document):
		article_version = ArticleVersion()
		article_version.addresses = db_document[Keys.ADDRESSES]
		article_version.allow_children = db_document[Keys.ALLOW_CHILDREN]
		article_version.article_uuid = db_document[Keys.TARGET_UUID]
		article_version.creation_date = db_document[Keys.CREATION_DATE]
		article_version.editable_by_others = db_document[Keys.EDITABLE_BY_OTHERS]
		article_version.editor_account_id = db_document[Keys.EDITOR_ACCOUNT_ID]
		article_version.parent_article_uuids = db_document[Keys.PARENT_UUID_ARRAY]
		article_version.publication_date = db_document[Keys.PUBLICATION_DATE]
		article_version.version_number = db_document[Keys.VERSION_NUMBER]
		article_version.uuid = db_document['_id']
		article_version.filename = db_document[Keys.FILENAME]
		article_version.view_mode = db_document.get(Keys.VIEW_MODE)
		
		if Keys.TITLE_TEXT_ID in db_document \
		and db_document[Keys.TITLE_TEXT_ID] is not None:
			article_version.title = self._text_res_pool.get_text(
				db_document[Keys.TITLE_TEXT_ID])
		
		if Keys.TEXT_ID in db_document and db_document[Keys.TEXT_ID] is not None:
			article_version.text = self._text_res_pool.get_text(
				db_document[Keys.TEXT_ID])
		
		if Keys.FILE_ID in db_document and db_document[Keys.FILE_ID] is not None:
			article_version.file = self._file_res_pool.get_file(
				db_document[Keys.FILE_ID])
		
		if Keys.REASON_ID in db_document:
			article_version.reason = self._text_res_pool.get_text(
				db_document[Keys.REASON_ID])
		
		return article_version
	
	def save_article_version(self, article_version):
		if not article_version.article_uuid:
			article_version.article_uuid = uuid.uuid4()
		
		assert isinstance(article_version.uuid, uuid.UUID)
		assert isinstance(article_version.article_uuid, uuid.UUID)
		
		article_version_d = {
			'_id': article_version.uuid,
			Keys.ADDRESSES: article_version.addresses,
			Keys.ALLOW_CHILDREN: article_version.allow_children,
			Keys.CREATION_DATE: article_version.creation_date,
			Keys.EDITABLE_BY_OTHERS: article_version.editable_by_others,
			Keys.EDITOR_ACCOUNT_ID: article_version.editor_account_id,
			Keys.PARENT_UUID_ARRAY: article_version.parent_article_uuids,
			Keys.PUBLICATION_DATE: article_version.publication_date,
			Keys.TARGET_UUID: article_version.article_uuid,
			Keys.FILENAME: article_version.filename,
			Keys.VIEW_MODE: article_version.view_mode
		}
		
		if article_version.text:
			article_version_d[Keys.TEXT_ID] = self._text_res_pool.set_text(
				article_version.text)
		
		if article_version.file:
			article_version_d[Keys.FILE_ID] = self._file_res_pool.set_file(
				article_version.file)
		
		if article_version.title:
			article_version_d[Keys.TITLE_TEXT_ID] = self._text_res_pool.set_text(
				article_version.title)
		
		if article_version.reason:
			article_version_d[Keys.REASON_ID] = self._text_res_pool.set_text(
				article_version.reason)
		
		self._db[self._col_names['versions']].save(article_version_d)
		
		for address in article_version.addresses:
			result = self.look_up_address(address)
			
			if result and result != article_version.article_uuid:
				raise Exception('Address is already used by %s' % result[Keys.TARGET_UUID])
		
		paths = self._get_parent_uuids(article_version)
		ancestors = []
		
		if paths:
			for path in paths:
				ancestors.extend(path)
		
		article_d = {
			Keys.TITLE: article_version.title or article_version.filename,
			Keys.PUBLICATION_DATE: article_version.publication_date or
				article_version.creation_date,
			Keys.PARENT_UUID_ARRAY: article_version.parent_article_uuids,
			Keys.ANCESTOR_UUID_ARRAY: ancestors,
			Keys.ADDRESSES: article_version.addresses,
			Keys.VIEW_MODE: article_version.view_mode,
		}
		
		if not self._db[self._col_names['articles']].find_one(
		{'_id': article_version.article_uuid}):
			self._db[self._col_names['versions']].update(
				{'_id': article_version.uuid},
				{'$set': {
					Keys.VERSION_NUMBER: 1
				}},
			)
			
			article_d['_id'] = article_version.article_uuid
			article_d[Keys.CURRENT_VERSION_NUMBER] = 1
			article_d[Keys.AUTHOR_ACCOUNT_ID] = article_version.editor_account_id
			self._db[self._col_names['articles']].insert(article_d, safe=True)
		else:
			result = self._db[self._col_names['articles']].find_and_modify(
				{'_id': article_version.article_uuid},
				{'$set': article_d,
				'$inc': { Keys.CURRENT_VERSION_NUMBER: 1},
				},
				new=True,
			)
			
			self._db[self._col_names['versions']].update(
				{'_id': article_version.uuid},
				{'$set': {
					Keys.VERSION_NUMBER: result[Keys.CURRENT_VERSION_NUMBER]
				}},
			)
			
	def _get_parent_uuids(self, article_version):
		results = self._get_parent_uuids_recursive(article_version)
		paths = []
		l = []
		
		for uuid in results:
			if uuid is None and l:
				paths.append(l)
				l = []
			elif uuid is not None:
				l.append(uuid)
		
		if l:
			paths.append(l)
		
		if paths and paths[0]:
			return paths
	
	def _get_parent_uuids_recursive(self, article_version, trail=[], head=True):
		if not head:
			trail.insert(0, article_version.article_uuid)
		
		if not article_version.parent_article_uuids:
			trail.append(None)
			return trail
		
		results = []
		
		for parent_uuid in article_version.parent_article_uuids:
			parent_article_version = self.get_article_version(article_uuid=parent_uuid)
			result = self._get_parent_uuids_recursive(parent_article_version, list(trail), False)
			
			if result:
				results.extend(result)
		
		return results
	
	def browse_articles(self, offset=0, limit=50, filter=None, 
	sort=Manager.SORT_TITLE, descending=False, parent_uuid=None, descendants=None):
		query = {}
		ordering = pymongo.DESCENDING if descending else pymongo.ASCENDING
		
		if sort == Manager.SORT_TITLE:
			sort_ = [(Keys.TITLE, ordering)]
		else:
			sort_ = [(Keys.PUBLICATION_DATE, ordering)]
		
		if parent_uuid and descendants:
			query = {Keys.ANCESTOR_UUID_ARRAY: parent_uuid}
		elif parent_uuid:
			query = {Keys.PARENT_UUID_ARRAY: parent_uuid}
		
		results = self._db[self._col_names['articles']].find(query,
			skip=offset, limit=limit, sort=sort_)
		
		for result in results:
			yield self._populate_article(result)
	
	def browse_article_versions(self, offset=0, limit=50, filter=None,
	sort=Manager.SORT_DATE, descending=True):
		ordering = pymongo.DESCENDING if descending else pymongo.ASCENDING
		
		if sort == Manager.SORT_TITLE:
			sort_ = [(Keys.TITLE, ordering)]
		else:
			sort_ = [(Keys.PUBLICATION_DATE, ordering)]
		
		results = self._db[self._col_names['versions']].find({},
			skip=offset, limit=limit, sort=sort_)
		
		for result in results:
			yield self._populate_article_version(result)
	
	def import_articles(self, file_obj, account_id_fn=None):
		reader = csv.reader(file_obj)
		
		for row in reader:
			primary_address = json.loads(row[4])
			
			if primary_address:
				addrs1 = frozenset([primary_address])
			else:
				addrs1 = frozenset([])
			
			addrs2 = frozenset(json.loads(row[3]) or [])
			addresses = list(addrs1) + list(addrs2 - addrs1)
			
			account_id = None
			author_account_id = None
			if account_id_fn:
				account_id = account_id_fn(json.loads(row[6]))
				author_account_id = account_id_fn(json.loads(row[16]))
			
			reason_id = None
			
			if json.loads(row[9]):
				reason_id = self._text_res_pool.set_text(json.loads(row[9]))
			
			title_text = json.loads(row[10])
			title_text_id = None
			
			if title_text:
				title_text_id = self._text_res_pool.set_text(title_text)
			
			text_id = None
			file_id = None
			
			text = json.loads(row[13])
			
			if text:
				text_id = self._text_res_pool.set_text(text)
			
			file_data = row[14]
			
			if file_data:
				f = cStringIO.StringIO(file_data.decode('base64'))
				f.seek(0)
				file_id = self._file_res_pool.set_file(f)
			
			view_mode = VIEW_TYPE_MAP.get(json.loads(row[16]))
			
			d = {
				Keys.TARGET_UUID: uuid.UUID(hex=row[0]),
				'_id': uuid.UUID(hex=row[1]),
				Keys.VERSION_NUMBER: int(row[2]),
				Keys.ADDRESSES: addresses,
				Keys.CREATION_DATE: iso8601.parse_date(row[5]),
				Keys.EDITOR_ACCOUNT_ID: account_id,
				Keys.PARENT_UUID_ARRAY: [uuid.UUID(hex=s) for s in json.loads(row[7])],
				Keys.PUBLICATION_DATE: iso8601.parse_date(row[8]),
				Keys.REASON_ID: reason_id,
				Keys.TITLE_TEXT_ID: title_text_id,
				Keys.EDITABLE_BY_OTHERS: json.loads(row[11]),
				Keys.ALLOW_CHILDREN: json.loads(row[12]),
				Keys.TEXT_ID: text_id,
				Keys.FILE_ID: file_id,
				Keys.FILENAME: json.loads(row[15]),
				Keys.VIEW_MODE: view_mode,
			}
			
			self._db[self._col_names['versions']].insert(d, safe=True)
			
			result = self._db[self._col_names['articles']].find_one(
				{'_id': d[Keys.TARGET_UUID]}
			)
			
			if not result or result and result[Keys.CURRENT_VERSION_NUMBER] < d[Keys.VERSION_NUMBER]:
				self._db[self._col_names['articles']].save(
					{'_id': d[Keys.TARGET_UUID],
					Keys.TITLE: title_text or json.loads(row[15]),
					Keys.PUBLICATION_DATE: d[Keys.PUBLICATION_DATE],
					Keys.CURRENT_VERSION_NUMBER: d[Keys.VERSION_NUMBER], 
					Keys.AUTHOR_ACCOUNT_ID: author_account_id,
					Keys.ADDRESSES: addresses,
					Keys.VIEW_MODE: view_mode, 
					},
					safe=True,
				)
		
		for result in self._db[self._col_names['versions']].find():
			paths = self._get_parent_uuids(
				self._populate_article_version(result))
			ancestors = []
			
			if paths:
				for path in paths:
					ancestors.extend(path)
			
			self._db[self._col_names['articles']].update(
				{'_id':result[Keys.TARGET_UUID]},
				{'$set': {
					Keys.PARENT_UUID_ARRAY: result[Keys.PARENT_UUID_ARRAY],
					Keys.ANCESTOR_UUID_ARRAY: ancestors,
				}})
	
	def export_articles(self, file_obj, articles=None):
		# TODO:
		pass

Manager.register(ManagerOnMongo)
