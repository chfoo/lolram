import base64
import bson
import datetime
import json
import logging
import os

_logger = logging.getLogger(__name__)


class SessionHandlerMixIn(object):
	MAX_COOKIE_AGE = 274 # 9 months
	COOKIE_NAME = 'torsid'
	
	@property
	def session(self):
		return self._get_session_dict()
	
	@property
	def _session_collection(self):
		return self.app_controller.database.sessions
	
	def _get_session_dict(self):
		if hasattr(self, '_session_dict'):
			return self._session_dict
		
		cookie_value = self.get_secure_cookie(SessionHandlerMixIn.COOKIE_NAME, 
			max_age_days=SessionHandlerMixIn.MAX_COOKIE_AGE)
		
		self._session_key = None
		self._session_id = None
		
		if not cookie_value:
			session_dict  = {}
		else:
			id_, key = self._unpack_cookie_value(cookie_value.decode())
			result = self._get_session_data_from_db(id_, key)
			
			_logger.debug('Session query result=%s', result)
			
			if result:
				session_dict = json.loads(result['data'])
				self._session_id = id_
				
				# TODO: key renewal by not supplying key
				self._session_key = key
				
				_logger.debug('Got session id=%s', id_)
			else:
				session_dict = {}
		
		self._session_dict = session_dict
		
		return session_dict
		
	def _unpack_cookie_value(self, cookie_value):
		id_, key = cookie_value.split(':', 2)
		return (bson.ObjectId(id_), base64.b16decode(key.encode()))
	
	def _pack_cookie_value(self, id_, key):
		return '%s:%s' % (id_, base64.b16encode(key).decode())
	
	def _save_session_object(self):
		id_ = self._session_id
		key = self._session_key or os.urandom(2)
		new_id = self._save_session_data_to_db(id_, key, 
			json.dumps(self._session_dict))
		
		if id_ is None:
			self.set_secure_cookie(SessionHandlerMixIn.COOKIE_NAME,
				self._pack_cookie_value(id_ or new_id, key),
				expires_days=SessionHandlerMixIn.MAX_COOKIE_AGE,
			)
		
	def _get_session_data_from_db(self, id_, key):
		return self._session_collection.find_one({
			'_id': id_,
			'key': key,
		})
	
	def _save_session_data_to_db(self, id_, key, data):
		d = {
			'key': key,
			'data': data,
			'modified': datetime.datetime.utcnow(),
		}
		
		if id_:
			d['_id'] = id_
		
		return self._session_collection.save(d, manipulate=id_ is None)
	
	def session_commit(self):
		if hasattr(self, '_session_dict'):
			self._save_session_object()
			_logger.debug('Commit session id=%s', self._session_id)


