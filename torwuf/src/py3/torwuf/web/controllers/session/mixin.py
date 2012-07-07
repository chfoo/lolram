'''Mixins for cookie sessions'''
#
#    Copyright (c) 2012 Christopher Foo <chris.foo@gmail.com>
#
#    This file is part of Torwuf.
#
#    Torwuf is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Torwuf is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Torwuf.  If not, see <http://www.gnu.org/licenses/>.
#
from torwuf.web.models.session import SessionCollection
import base64
import bson
import contextlib
import datetime
import json
import logging
import os

_logger = logging.getLogger(__name__)


class SessionDict(dict):
    __slots__ = ('object_id', 'secret_key')


class SessionHandlerMixIn(object):
    MAX_COOKIE_AGE = 274  # 9 months
    PERSISTENT_COOKIE_NAME = 'torpsid'
    SESSION_COOKIE_NAME = 'torsid'

    @property
    def session(self):
        return self._get_session_dict()

    @contextlib.contextmanager
    def get_session(self):
        try:
            yield self._get_session_dict()
        except Exception as e:
            # TODO: rollback
            raise e
        else:
            self.session_commit()

    @property
    def persistent_session(self):
        return self._get_session_dict(persistent=True)

    @contextlib.contextmanager
    def get_persistent_session(self):
        try:
            yield self._get_session_dict(persistent=True)
        except Exception as e:
            # TODO: rollback
            raise e
        else:
            self.session_commit()

    def session_get_any(self, key, default=None):
        return self.session.get(key, None) \
            or self.persistent_session.get(key, default)

    @property
    def _session_collection(self):
        return self.app_controller.database[SessionCollection.COLLECTION]

    def _get_session_dict(self, persistent=False):
        if persistent:
            if hasattr(self, '_persistent_session_dict'):
                return self._persistent_session_dict
        else:
            if hasattr(self, '_session_dict'):
                return self._session_dict

        session_dict = SessionDict()
        session_dict.object_id = None
        session_dict.secret_key = None

        if persistent:
            cookie_name = SessionHandlerMixIn.PERSISTENT_COOKIE_NAME
        else:
            cookie_name = SessionHandlerMixIn.SESSION_COOKIE_NAME

        cookie_value = self.get_secure_cookie(cookie_name,
            max_age_days=SessionHandlerMixIn.MAX_COOKIE_AGE)

        if cookie_value:
            object_id, secret_key = self._unpack_cookie_value(
                cookie_value.decode())
            result = self._get_session_data_from_db(object_id, secret_key)

            if result:
                session_dict.update(json.loads(result['data']))
                session_dict.object_id = object_id

                # TODO: key renewal by not supplying key
                session_dict.secret_key = secret_key

                _logger.debug('Got session id=%s persistent=%s', object_id,
                    persistent,
                )

        if persistent:
            self._persistent_session_dict = session_dict
        else:
            self._session_dict = session_dict

        return session_dict

    def _unpack_cookie_value(self, cookie_value):
        id_, key = cookie_value.split(':', 2)
        return (bson.ObjectId(id_), base64.b16decode(key.encode()))

    def _pack_cookie_value(self, id_, key):
        return '%s:%s' % (id_, base64.b16encode(key).decode())

    def _save_session_object(self, persistent=False):
        if persistent:
            if hasattr(self, '_persistent_session_dict'):
                session_dict = self._persistent_session_dict
            else:
                return
        else:
            if hasattr(self, '_session_dict'):
                session_dict = self._session_dict
            else:
                return

        # TODO: might want to check if object is actually dirty before continue

        if not session_dict.secret_key:
            session_dict.secret_key = os.urandom(2)

        _logger.debug('Commit session id=%s persistent=%s',
            session_dict.object_id, persistent,
        )
        new_object_id = self._save_session_data_to_db(session_dict.object_id,
            session_dict.secret_key,
            json.dumps(session_dict)
        )

        if not session_dict.object_id:
            session_dict.object_id = new_object_id

            if persistent:
                cookie_name = SessionHandlerMixIn.PERSISTENT_COOKIE_NAME
            else:
                cookie_name = SessionHandlerMixIn.SESSION_COOKIE_NAME

            _logger.debug('Setting new session cookie id=%s persistent=%s',
                session_dict.object_id, persistent,
            )
            self.set_secure_cookie(cookie_name,
                self._pack_cookie_value(session_dict.object_id,
                    session_dict.secret_key),
                expires_days=None,
            )

    def _get_session_data_from_db(self, object_id, secret_key):
        return self._session_collection.find_one({
            '_id': object_id,
            SessionCollection.SECRET_KEY: secret_key,
        })

    def _save_session_data_to_db(self, object_id, secret_key, data):
        d = {
            'key': secret_key,
            SessionCollection.DATA_BYTES: data,
            SessionCollection.DATE_MODIFIED: datetime.datetime.utcnow(),
        }

        if object_id:
            d['_id'] = object_id

        return self._session_collection.save(d)

    def session_commit(self):
        self._save_session_object()
        self._save_session_object(persistent=True)
