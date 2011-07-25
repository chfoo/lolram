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

import hashlib

from bitstring.constbitarray import ConstBitArray
from lolram2.respool import TextResPool, TextResource
from pymongo.binary import Binary


class TextResPoolOnMongo(object):
	def set_mongo_collection(self, collection):
		self._collection = collection
	
	def get_text(self, id):
		hash = ConstBitArray(length=256, int=id).bytes
		result = self._collection.find_one({'_id': Binary(hash)})
		
		if result is not None:
			s = TextResource(result['text'])
			s.hash = hash
			s.id = id
			
			return s
	
	def set_text(self, text, create=True):
		hash = hashlib.sha256(text).digest()
		
		result = self._collection.find_one({'_id': Binary(hash)})
		
		if result:
			return ConstBitArray(bytes=hash).int
		
		elif create:
			self._collection.insert({
				'_id':Binary(hash),
				'text': text
			})
			
			return ConstBitArray(bytes=hash).int

TextResPool.register(TextResPoolOnMongo)