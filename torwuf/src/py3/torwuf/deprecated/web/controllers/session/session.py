'''Sessions using cookies controller'''
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
from torwuf.deprecated.web.models.session import SessionCollection
import datetime
import threading
import time
import torwuf.deprecated.web.controllers.base


class SessionController(torwuf.deprecated.web.controllers.base.BaseController):
    DAYS_4 = 345600

    def init(self):
        self.add_url_spec('/session/test', TestHandler)

        self.clean_timer = threading.Timer(SessionController.DAYS_4,
            self.clean_old_sessions)
        self.clean_timer.start()
        self.clean_old_sessions()

    def clean_old_sessions(self):
        date_nine_months_ago = datetime.datetime.utcfromtimestamp(
            time.time() - 23667694)
        self.application.database[SessionCollection.COLLECTION].remove({
            SessionCollection.DATE_MODIFIED: {'$lt': date_nine_months_ago}
        })


class TestHandler(torwuf.deprecated.web.controllers.base.BaseHandler):
    name = 'session_test'
    KEY = 'session_test_text'
    PERSISTENT_KEY = 'persistent_session_test_text'

    def get(self):
        self.add_message('hello')

        self.render('session/test.html',
            text=self.session.get(TestHandler.KEY, ''),
            persistent_text=self.persistent_session.get(
                TestHandler.PERSISTENT_KEY, ''),
        )

    def post(self):
        with self.get_session() as session, \
        self.get_persistent_session() as persistent_session:
            session[TestHandler.KEY] = self.get_argument('text', '')
            persistent_session[TestHandler.PERSISTENT_KEY] = self.get_argument(
                'persistent_text', '')

        self.add_message('Text saved')

        self.redirect(self.reverse_url(TestHandler.name))
#        self.render('session/test.html',
#            text=self.session.get(TestHandler.KEY, ''),
#            persistent_text=self.persistent_session.get(
#                TestHandler.PERSISTENT_KEY, ''),
#        )
