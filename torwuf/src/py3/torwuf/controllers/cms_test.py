'''Test the cms controller'''
# This file is part of Torwuf.
# Copyright © 2012 Christopher Foo <chris.foo@gmail.com>.
# Licensed under GNU GPLv3. See COPYING.txt for details.
from tornado.httpclient import HTTPRequest
from torwuf.controllers.base import bytes_to_b32low_str
from torwuf.controllers.testing import BaseTestCase
import http.client
import json
import unittest
import urllib.parse
import uuid


class TestCMS(BaseTestCase):
    def test_new_article(self):
        uuid_obj = uuid.uuid4()

        self.http_client.fetch(HTTPRequest(self.get_url('/cms/article/new'),
            method='POST',
            body=urllib.parse.urlencode({
                'title': 'my title',
                'text': 'my test',
                'date': '2000-01-01 00:00:00',
                'uuid': str(uuid_obj),
                '_render_format': 'json',
                'save': 'save',
            }),
            headers={'X-Testing-Key': self.testing_key},
        ), self.stop)

        response = self.wait()

        self.assertEqual(response.code, http.client.OK)
        response_dict = json.loads(response.body.decode())
        uuid_obj = uuid.UUID(response_dict['uuid'])
        doc_id = response_dict['id']

        self.http_client.fetch(
            self.get_url('/a/' + bytes_to_b32low_str(uuid_obj.bytes)),
            self.stop)

        response = self.wait()
        self.assertEqual(response.code, http.client.OK)
        response_text = response.body.decode()
        self.assertIn('my test', response_text)

        self.http_client.fetch(HTTPRequest(
            self.get_url('/cms/article/delete/' + doc_id),
            method='POST',
            body=urllib.parse.urlencode(
                {'_render_format': 'json', 'confirm': 'confirm'}
            ),
            headers={'X-Testing-Key': self.testing_key}
        ), self.stop)

        response = self.wait()

        self.assertEqual(response.code, http.client.OK)

        self.http_client.fetch('/a/' + bytes_to_b32low_str(uuid_obj.bytes),
            self.stop)

        response = self.wait()

        self.assertEqual(response.code, http.client.NOT_FOUND)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
