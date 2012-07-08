'''RequestHandler mixins for authentication'''
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
from torwuf.deprecated.web.models.authentication import SessionKeys
import base64
import uuid


class AuthenticationHandlerMixIn(object):
    def get_current_user(self):
        current_account_id = self.session_get_any(
            SessionKeys.CURRENT_ACCOUNT_ID)

        if current_account_id:
            return 'account:%s' % current_account_id

        openid_id = self.session_get_any(SessionKeys.CURRENT_OPENID)

        if openid_id:
            return 'openid:%s' % openid_id

        if self.app_controller.config.config_parser.getboolean('account',
        'use_dummy_localhost_account', fallback=False) \
        and self.request.host.split(':', 1)[0] in ('localhost', '127.0.0.1',
        'localdev.torwuf.com'):
            return 'test:localhost'

    @property
    def current_account_id(self):
        return self.session_get_any(SessionKeys.CURRENT_ACCOUNT_ID)

    @current_account_id.setter
    def current_account_id(self, str_or_byte_id):
        if isinstance(str_or_byte_id, str):
            self.session[SessionKeys.CURRENT_ACCOUNT_ID] = \
                str_or_byte_id.lower()
        else:
            self.session[SessionKeys.CURRENT_ACCOUNT_ID] = str(
                base64.b16encode(str_or_byte_id), 'utf8').lower()

    @property
    def current_account_uuid(self):
        hex_str = self.current_account_id

        if hex_str:
            return uuid.UUID(hex_str)

    @property
    def current_openid(self):
        return self.session_get_any(SessionKeys.CURRENT_OPENID)

    def logout(self):
        self.session.pop(SessionKeys.CURRENT_ACCOUNT_ID, None)
        self.session.pop(SessionKeys.CURRENT_OPENID, None)
        self.persistent_session.pop(SessionKeys.CURRENT_ACCOUNT_ID, None)
        self.persistent_session.pop(SessionKeys.CURRENT_OPENID, None)


class ProcessingMixIn(object):
    # XXX: It is important that realm must stay static as much as possible
    # Otherwise Google will return useless identity urls
    def get_openid_realm(self):
        if self.request.host.split(':', 1)[0] in ('localhost', '127.0.0.1'):
            return self.request.protocol + '://' + self.request.host
        else:
            return self.request.protocol + '://*.' + self.request.host
