# This file is part of Torwuf.
# Copyright © 2012 Christopher Foo <chris.foo@gmail.com>.
# Licensed under GNU GPLv3. See COPYING.txt for details.
from torwuf.controllers.testing import BaseTestCase


class TestApp(BaseTestCase):
    def  test_smoke_minimal(self):
        '''It should not crash when launched'''

        self.http_client.fetch(self.get_url('/'), self.stop)
        self.wait()
