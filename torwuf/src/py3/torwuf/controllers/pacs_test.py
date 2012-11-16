'''Test the pacs controller'''
# This file is part of Torwuf.
# Copyright © 2012 Christopher Foo <chris.foo@gmail.com>.
# Licensed under GNU GPLv3. See COPYING.txt for details.
from tornado.httpclient import HTTPRequest
from torwuf.controllers.testing import BaseTestCase
import http.client
import json
import tornado.escape
import unittest.main
import urllib.parse


class TestPacs(BaseTestCase):
    UNIQUE_PAC = '(397c756b-7810-4141-8701-739d9c4ffbca<'

    def test_new(self):
        self.http_client.fetch(HTTPRequest(
            self.get_url('/pacs/new'),
            body=urllib.parse.urlencode({
                'text': TestPacs.UNIQUE_PAC,
                'tags': '"two word" my_tag',
                '_render_format': 'json',
            }),
            method='POST',
            headers={'X-Testing-Key': self.testing_key},
        ), self.stop)

        response = self.wait()

        self.assertEqual(response.code, http.client.OK)
        response_dict = json.loads(response.body.decode())
        pac_id = response_dict['id']

        self.http_client.fetch(self.get_url('/pacs/' + pac_id), self.stop)
        response = self.wait()
        self.assertEqual(response.code, http.client.OK)
        response_text = response.body.decode()

        self.assertIn(tornado.escape.xhtml_escape(TestPacs.UNIQUE_PAC),
            response_text)

        self.http_client.fetch(self.get_url('/pacs/'), self.stop)
        response = self.wait()
        self.assertEqual(response.code, http.client.OK)
        response_text = response.body.decode()

        self.assertIn(tornado.escape.xhtml_escape(TestPacs.UNIQUE_PAC),
            response_text)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
