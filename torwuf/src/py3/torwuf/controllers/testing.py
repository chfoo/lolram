# This file is part of Torwuf.
# Copyright © 2012 Christopher Foo <chris.foo@gmail.com>.
# Licensed under GNU GPLv3. See COPYING.txt for details.
from pywheel.web.bootstrap import Bootstrap
from torwuf.controllers.app import Application
import os.path
import time
import tornado.testing
import torwuf


class BaseTestCase(tornado.testing.AsyncHTTPTestCase):
    def __init__(self, *args, **kwargs):
        self.testing_key = 'iHrlXxwxX8bHbRNgdBFsLUFiZtrX2v5M'
        tornado.testing.AsyncHTTPTestCase.__init__(self, *args, **kwargs)

    def get_app(self):
        conf_file_path = os.path.join(os.path.dirname(torwuf.__file__),
            'sample.conf')
        boostrap = Bootstrap(argv=['--config', conf_file_path])
        app = Application(bootstrap=boostrap, testing_key=self.testing_key)

        # XXX: wait for stuff to start up
        time.sleep(0.1)

        return app
