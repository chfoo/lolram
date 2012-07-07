'''Test the pacs controller'''
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
import json
import tornado.escape
import torwuf.tests.web.server_base
import unittest


class TestPacs(unittest.TestCase,
torwuf.tests.web.server_base.ServerBaseMixIn):
    UNIQUE_PAC = '(397c756b-7810-4141-8701-739d9c4ffbca<'

    def setUp(self):
        self.create_app()
        self.start_server()

    def tearDown(self):
        self.stop_server()

    def test_new(self):
        response = self.request('/pacs/new',
            query_map={
                'text': TestPacs.UNIQUE_PAC,
                'tags': '"two word" my_tag',
                '_render_format': 'json',
            },
            method='POST',
        )

        self.assertEqual(response.status, http.client.OK)
        response_dict = json.loads(response.read().decode())
        pac_id = response_dict['id']

        response = self.request('/pacs/' + pac_id)
        self.assertEqual(response.status, http.client.OK)
        response_text = response.read().decode()

        self.assertIn(tornado.escape.xhtml_escape(TestPacs.UNIQUE_PAC),
            response_text)

        response = self.request('/pacs/')
        self.assertEqual(response.status, http.client.OK)
        response_text = response.read().decode()

        self.assertIn(tornado.escape.xhtml_escape(TestPacs.UNIQUE_PAC),
            response_text)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
