'''Things that controllers and handlers should inherit'''
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
from torwuf.web.controllers.account.authentication.mixins import \
    AuthenticationHandlerMixIn
from torwuf.web.controllers.session.mixin import SessionHandlerMixIn
from torwuf.web.utils import json_serializer
import json
import logging
import lolram.deprecated.web.framework.app
import torwuf.web.controllers.error

_logger = logging.getLogger(__name__)


class BaseController(lolram.deprecated.web.framework.app.BaseController):
    pass


class BaseHandler(lolram.deprecated.web.framework.app.BaseHandler,
torwuf.web.controllers.error.ErrorOutputHandlerMixin,
SessionHandlerMixIn,
AuthenticationHandlerMixIn,
):
    MESSAGE_SESSION_KEY = '_messages'

    def is_testing_key_valid(self):
        if 'Testing-Key' in self.request.headers:
            local_key = self.controller.application.config.\
                config_parser['account']['testing_key']
            client_key = self.request.headers['Testing-Key']

            return local_key == client_key

    def check_xsrf_cookie(self):
        if self.is_testing_key_valid():
            return

        lolram.deprecated.web.framework.app.BaseHandler.check_xsrf_cookie(self)

    def write_error(self, *args, **kargs):
        torwuf.web.controllers.error.\
            ErrorOutputHandlerMixin.write_error(self, *args, **kargs)

    def get_current_user(self):
        return AuthenticationHandlerMixIn.get_current_user(self)

    def render(self, template_name, **kargs):
        if BaseHandler.MESSAGE_SESSION_KEY in self.session:
            if not hasattr(self.request, 'messages'):
                self.request.messages = []

            self.request.messages.extend(
                self.session[BaseHandler.MESSAGE_SESSION_KEY])

        if self.get_argument('_render_format', False) == 'json':
            self.render_json(kargs)
        else:
            lolram.deprecated.web.framework.app.BaseHandler.render(
                self, template_name, **kargs)

    def render_json(self, data):
        if BaseHandler.MESSAGE_SESSION_KEY in self.session:
            data['_messages'] = self.request.messages

        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(data, default=json_serializer))
        self.finish()

    def redirect(self, url, permanent=False, status=None, api_data=None):
        if self.get_argument('_render_format', False) == 'json':
            self.render_json(api_data)
        else:
            lolram.deprecated.web.framework.app.BaseHandler.redirect(
                self, url, permanent, status)

    def add_message(self, title, body=None):
        if not hasattr(self.request, 'messages'):
            self.request.messages = []

        self.request.messages.append((title, body))

    def finish(self, chunk=None):
        if hasattr(self.request, 'messages') and self.request.messages:
            with self.get_session() as session:
                session[BaseHandler.MESSAGE_SESSION_KEY
                    ] = self.request.messages
        elif hasattr(self.request, 'messages'):
            with self.get_session() as session:
                session.pop(BaseHandler.MESSAGE_SESSION_KEY, None)

        lolram.deprecated.web.framework.app.BaseHandler.finish(self, chunk)
