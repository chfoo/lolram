# This file is part of Torwuf.
# Copyright © 2012 Christopher Foo <chris.foo@gmail.com>.
# Licensed under GNU GPLv3. See COPYING.txt for details.
from pywheel.backoff import Trier, ExpBackoff
from pywheel.db.mongodb import SessionController, Reconnector
from torwuf.controllers import xkcd_geocities, pacs, cms, bzr, index
from torwuf.controllers.bzr import BzrController
from torwuf.controllers.cms import CMSController
from torwuf.controllers.index import CatchAllHandler
from torwuf.controllers.pacs import PacsController
from torwuf.controllers.xkcd_geocities import XKCDGeocitiesController
from torwuf.views import templates_dir
import logging
import os.path
import tornado.web
import torwuf.views

_logger = logging.getLogger(__name__)


class Application(tornado.web.Application):
    def __init__(self, bootstrap, testing_key=None):
        self._bootstrap = bootstrap
        self.testing_key = testing_key
        conf = self.config_parser = bootstrap.config_parser

        self._setup_db()

        Trier(self._setup_session_controller, backoff=ExpBackoff(cap=300))

        url_specs = []

        url_specs.extend(index.url_specs)
        url_specs.extend(xkcd_geocities.url_specs)
        url_specs.extend(pacs.url_specs)
        url_specs.extend(cms.url_specs)
        url_specs.extend(bzr.url_specs)
        url_specs.append((r'/(.*)', CatchAllHandler))

        tornado.web.Application.__init__(self,
            url_specs,
            cookie_secret=conf['application']['cookie_secret'],
            xsrf_cookies=True,
            template_path=templates_dir,
            static_path=os.path.join(os.path.dirname(torwuf.views.__file__),
                'resources'),
        )

        self.root_path = conf['application']['root-path']
        self.db_path = os.path.join(self.root_path, 'databases')
        self.upload_path = os.path.join(self.root_path, 'uploads')
        self.xkcd_geocities = XKCDGeocitiesController(os.path.join(
            self.db_path, 'xkcd_geocities'))
        self.pacs_controller = PacsController(self)
        self.cms = CMSController(self)
        self.bzr = BzrController(self)
        self.login_rate_limit_controller = self.bzr.login_rate_limit_controller

    def _setup_db(self):
        conf = self._bootstrap.config_parser
        self._db_name = conf['mongodb']['database']
        self._db_username = conf['mongodb']['username']
        self._db_password = conf['mongodb']['password']
        self._db_reconnector = Reconnector()

    def _setup_session_controller(self):
        if not self.db:
            return False

        self._session_controller = SessionController(self.db['sessions'])
        return True

    @property
    def db(self):
        conn = self._db_reconnector.conn

        if not conn:
            _logger.debug('DB Connection not available')

            return None

        db = conn[self._db_name]
        db.authenticate(self._db_username, self._db_password)

        return db

    @property
    def session(self):
        return self._session_controller
