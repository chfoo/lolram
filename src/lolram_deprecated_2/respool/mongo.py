# encoding=utf8

'''MongoDB backend
'''

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

from lolram_deprecated_2.respool import TextResPool, TextResource
from pymongo.binary import Binary
import hashlib
import pymongo
import random

class TextResPoolOnMongo(TextResPool):
	def set_mongo_collection(self, collection):
		self._collection = collection
		self._collection.ensure_index([('nid', pymongo.ASCENDING)])
	
	def get_text(self, id):
		result = self._collection.find_one({'nid': id})
		
		if result is not None:
			s = TextResource(result['text'])
			s.hash = result['_id']
			s.id = id
			
			return s
	
	def set_text(self, text, create=True):
		if isinstance(text, unicode):
			hash = hashlib.sha256(text.encode('utf8')).digest()
		else:
			hash = hashlib.sha256(text).digest()
		
		result = self._collection.find_one({'_id': Binary(hash)})
		
		if result:
			return result['nid']
		
		elif create:
			while True:
				nid = random.randint(0, 2**31)
				
				if not self._collection.find_one({'nid':nid}):
					break
			
			self._collection.insert({
				'_id': Binary(hash),
				'text': text,
				'nid': nid
			})
			
			return nid

TextResPool.register(TextResPoolOnMongo)
