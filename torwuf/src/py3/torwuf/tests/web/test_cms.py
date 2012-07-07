'''Test the cms controller'''
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
from torwuf.web.utils import bytes_to_b32low_str
import http.client
import json
import torwuf.tests.web.server_base
import unittest
import uuid


class TestCMS(unittest.TestCase, torwuf.tests.web.server_base.ServerBaseMixIn):

    def setUp(self):
        self.create_app()
        self.start_server()

    def tearDown(self):
        self.stop_server()

    def test_new_article(self):
        uuid_obj = uuid.uuid4()

        response = self.request('/cms/article/new', method='POST', query_map={
            'title': 'my title',
            'text': 'my test',
            'date': '2000-01-01 00:00:00',
            'uuid': str(uuid_obj),
            '_render_format': 'json',
            'save': 'save',
        })

        self.assertEqual(response.status, http.client.OK)
        response_dict = json.loads(response.read().decode())
        uuid_obj = uuid.UUID(response_dict['uuid'])
        doc_id = response_dict['id']

        response = self.request('/a/' + bytes_to_b32low_str(uuid_obj.bytes))

        self.assertEqual(response.status, http.client.OK)
        response_text = response.read().decode()
        self.assertIn('my test', response_text)

        response = self.request('/cms/article/delete/' + doc_id, method='POST',
            query_map={'_render_format': 'json', 'confirm': 'confirm'},
        )

        self.assertEqual(response.status, http.client.OK)

        response = self.request('/a/' + bytes_to_b32low_str(uuid_obj.bytes))

        self.assertEqual(response.status, http.client.NOT_FOUND)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
