# encoding=utf8

'''Support for client sessions using cookies'''

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

import time
import datetime
import os
import base64

import bson.objectid


class SessionMongoDBMixIn(object):
	SESSION_MAX_AGE = 40 # days
	SESSION_DB_COLLECTION = 'session_cookie_data'
	SESSION_COOKIE_NAME = 'lolram_id'
	SESSION_COOKIE_KEY_MAX_AGE = 86400 # seconds
	SESSION_COOKIE_MAX_AGE = 23667694 # seconds
	
	class SessionDict(dict):
		def __init__(self, *args, **kargs):
			super(SessionMongoDBMixIn.SessionDict, self).__init__(*args, **kargs)
			self.id = None
			self.key = None
			self.timestamp = 0
			self.persistent = False
		
		@property
		def object_id(self):
			if self.id:
				bytes_ = base64.urlsafe_b64decode(self.id)
				return bson.objectid.ObjectId(bytes_)
		
		@object_id.setter
		def object_id(self, object_id):
			self.id = base64.urlsafe_b64encode(object_id.binary)
	
	@property
	def session(self):
		if hasattr(self, '_session_dict'):
			return self._session_dict
	
	def _set_session_cookie(self, persistent=False):
		value = '%s:%s' % (self.session.id, self.session.key)
		
		if self.session.persistent:
			expire_date = datetime.datetime.fromtimestamp(
				time.time() + self.SESSION_COOKIE_MAX_AGE)
		else:
			expire_date = None
		
		self.set_cookie(self.SESSION_COOKIE_NAME, value, expires=expire_date)
	
	def _init_new_session(self):
		self._session_dict = self.SessionDict()
	
	def clear_session(self):
		if self.session and self.session.object_id:
			self.db[self.SESSION_DB_COLLECTION].remove(
				{'_id': self.session.object_id})
		
		self.clear_cookie(self.SESSION_COOKIE_NAME)
		self._init_new_session()
	
	def setup_session(self):
		cookie_value = self.get_cookie(self.SESSION_COOKIE_NAME)
			
		if not cookie_value:
			self._init_new_session()
			return
		
		session_id, seperator, session_key = cookie_value.partition(':')
		seperator #UnusedVariable 
		
		try:
			bytes_ = base64.urlsafe_b64decode(session_id)
			object_id = bson.objectid.ObjectId(bytes_)
		except TypeError:
			self.clear_session()
			return
		except bson.errors.InvalidId:
			self.clear_session()
			return
		
		result = self.db[self.SESSION_DB_COLLECTION].find_one(
			{'_id': object_id, 'key': session_key})
		
		if result:
			self._session_dict = self.SessionDict(result.get('data', {}))
			self.session.id = session_id
			self.session.key = session_key
			self.session.timestamp = time.mktime(object_id.generation_time.utctimetuple())
		else:
			self.clear_session()
	
	def save_session(self):
		if self.session is None or not self.session and not self.session.id:
			return
		
		collection = self.db[self.SESSION_DB_COLLECTION]
		key_needs_renewal = time.time() - self.session.timestamp > \
			self.SESSION_COOKIE_KEY_MAX_AGE
			
		if key_needs_renewal:
			self.session.key = os.urandom(8).encode('hex')
		
		d = {
			'key': self.session.key,
			'data': self.session,
		}
		
		if self.session.object_id:	
			collection.update({'_id': bson.objectid.ObjectId(self.session.object_id)}, 
				{'$set': d})
		else:
			object_id = collection.insert(d)
			self.session.object_id = object_id
		
		if key_needs_renewal:
			self._set_session_cookie(self.session.persistent)
			

	