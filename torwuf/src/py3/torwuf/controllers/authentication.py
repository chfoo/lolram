# This file is part of Torwuf.
# Copyright © 2012 Christopher Foo <chris.foo@gmail.com>.
# Licensed under GNU GPLv3. See COPYING.txt for details.
from torwuf.controllers.base import BaseRequestHandler
import tornado.auth
import tornado.web


class SimpleGoogleLoginHandler(BaseRequestHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument('openid.mode', None):
            self.get_authenticated_user(self._auth_cb)
            return

        self.authenticate_redirect()

    def _auth_cb(self, user):
        if not user:
            raise tornado.web.HTTPError(500, "Google auth failed")

        with self.application.session(self) as s:
            s['user_email'] = user['email']

        self.redirect('/')
