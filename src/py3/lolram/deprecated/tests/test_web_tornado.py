#
#    Copyright © 2012 Christopher Foo <chris.foo@gmail.com>
#
#    This file is part of Lolram.
#
#    Lolram is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Lolram is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Lolram.  If not, see <http://www.gnu.org/licenses/>.
#
__docformat__ = 'restructuredtext en'

import lolram.deprecated.web.tornado
import unittest
import lolram.deprecated.tests.server_base


class TestTornadoApp(unittest.TestCase,
lolram.deprecated.tests.server_base.ServerBaseMixIn):
    def __init__(self, *args, **kargs):
        unittest.TestCase.__init__(self, *args, **kargs)
        self.app = lolram.deprecated.web.tornado.WSGIApplication()
        self.start_server()

    # TODO: write tests
#    def test_init(self):
#        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
