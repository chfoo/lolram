'''Pac-Man text art (ascii-pacs)'''
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
from torwuf.web.controllers.account.authorization.decorators import \
	require_group
from torwuf.web.models.pacs import PacsCollection, PacsTagsCollection
import bson.code
import bson.objectid
import pymongo
import shlex
import string
import torwuf.web.controllers.base

VALID_TAG_SET = frozenset(string.printable)
MAP_TAGS = bson.code.Code("function () {"
	"  this.tags.forEach(function(z) {"
	"    emit(z, 1);"
	"  });"
	"}")
REDUCE_TAGS = bson.code.Code("function (key, values) {"
	"  var total = 0;"
	"  for (var i = 0; i < values.length; i++) {"
	"    total += values[i];"
	"  }"
	"  return total;"
	"}")

class PacsController(torwuf.web.controllers.base.BaseController):
	def init(self):
		self.add_url_spec('/pacs/', ListAllHandler)
		self.add_url_spec('/pacs/new', NewHandler)
		self.add_url_spec('/pacs/mass_new', MassNewHandler)
		self.add_url_spec('/pacs/tag/(.*)', ListByTagHandler)
		self.add_url_spec(r'/pacs/([-{}a-zA-Z0-9]+)', ViewSingleHandler)
		self.add_url_spec(r'/pacs/([-{}a-zA-Z0-9]+)/edit', EditHandler)
		
		self.pac_collection.ensure_index([(PacsCollection.TAGS, pymongo.ASCENDING)])
	
	@property
	def pac_collection(self):
		return self.application.database[PacsCollection.COLLECTION]
	
	@property
	def tag_collection(self):
		return self.application.database[PacsTagsCollection.COLLECTION]
	
	def aggregate_tags(self):
		# XXX: for api 1.9 (2.1.1 out is a required argument)
		self.pac_collection.map_reduce(MAP_TAGS, REDUCE_TAGS, 
			out=PacsTagsCollection.COLLECTION)


class ListAllHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'pacs_list_all'
	
	def get(self):
		tag_dict = {}
		tag_results = self.controller.tag_collection.find()
		
		for result in tag_results:
			tag_dict[result['_id']] = result[PacsTagsCollection.COUNT] 
		
		results = self.controller.pac_collection.find(sort=[(PacsCollection.TAGS, 1)])
		
		self.render('pacs/list_all.html', PacsCollection=PacsCollection,
			results=results, tag_dict=tag_dict)
	
	
class NewHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'pacs_new'
	
	@require_group('pacs')
	def get(self):
		self.render('pacs/edit.html', text='', tags='')
	
	@require_group('pacs')
	def post(self):
		text = self.get_argument('text')
		tags = self.get_argument('tags', '')
		tag_list = list(sorted(frozenset(shlex.split(tags))))
		
		doc_id = self.controller.pac_collection.insert({
			PacsCollection.TEXT: text,
			PacsCollection.TAGS: tag_list
		})
		
		self.controller.aggregate_tags()
		
		self.redirect(self.reverse_url(ListAllHandler.name))

class MassNewHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'pacs_mass_new'
	SEPERATOR = '{4942fb40-a139-41ba-95a4-c692941e52a9}'
	
	@require_group('pacs')
	def get(self):
		self.render('pacs/mass_new.html', mass_text='', tags='', 
			seperator=MassNewHandler.SEPERATOR)
	
	@require_group('pacs')
	def post(self):
		mass_text = self.get_argument('mass_text')
		tags = self.get_argument('tags', '')
		tag_list = list(sorted(frozenset(shlex.split(tags))))
		
		for text in mass_text.split(MassNewHandler.SEPERATOR):
			doc_id = self.controller.pac_collection.insert({
				PacsCollection.TEXT: text,
				PacsCollection.TAGS: tag_list
			})
		
		self.controller.aggregate_tags()
		
		self.redirect(self.reverse_url(ListAllHandler.name))


def list_to_str(tags):
	escaped_list = []
	
	for tag in tags:
		if '"' in tag:
			tag = tag.replace('"', r'\"')
		
		if ' ' in tag:
			tag = '"%s"' % tag
		
		escaped_list.append(tag)
	
	return ' '.join(escaped_list)

class ViewSingleHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'pacs_view_single'
	
	def get(self, doc_hex_id):
		result = self.controller.pac_collection.find_one(bson.objectid.ObjectId(doc_hex_id))
		
		if result:
			self.render('pacs/view_single.html', result=result, PacsCollection=PacsCollection)
		else:
			raise HTTPError(404, 'pac not found')

class EditHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'pacs_edit'
	
	@require_group('pacs')
	def get(self, doc_hex_id):
		result = self.controller.pac_collection.find_one(bson.objectid.ObjectId(doc_hex_id))
		
		if result:
			text = result[PacsCollection.TEXT]
			tags = list_to_str(result[PacsCollection.TAGS])
		
			self.render('pacs/edit.html', text=text, tags=tags)
		else:
			raise HTTPError(404, 'pac not found')
	
	@require_group('pacs')
	def post(self, doc_hex_id):
		text = self.get_argument('text')
		tags = self.get_argument('tags', '')
		tag_list = list(sorted(frozenset(shlex.split(tags))))
		
		doc_id = self.controller.pac_collection.save({
			'_id': bson.objectid.ObjectId(doc_hex_id),
			PacsCollection.TEXT: text,
			PacsCollection.TAGS: tag_list
		})
		
		self.controller.aggregate_tags()
		
		self.redirect(self.reverse_url(ListAllHandler.name))
		
class ListByTagHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'pacs_list_by_tag'
	
	def get(self, tag_name):
		results = self.controller.pac_collection.find({
			PacsCollection.TAGS: tag_name,
		})
		
		if results.count():
			self.render('pacs/list_by_tag.html', PacsCollection=PacsCollection,
			results=results, tag=tag_name)
		else:
			raise HTTPError(404)
		
