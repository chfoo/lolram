'''Test the xkcd-geocities controller'''
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
import http.client
import torwuf.tests.web.server_base
import unittest


@unittest.skip("Don't hammer xkcd.com")
class TestXkcdGeocities(unittest.TestCase,
torwuf.tests.web.server_base.ServerBaseMixIn):
    def setUp(self):
        self.create_app()
        self.start_server()

    def tearDown(self):
        self.stop_server()

    def test_basic(self):
        response = self.request('/xkcd-geocities/')
        self.assertEqual(response.status, http.client.OK)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
