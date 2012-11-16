'''Test the bzr controller'''
# This file is part of Torwuf.
# Copyright © 2012 Christopher Foo <chris.foo@gmail.com>.
# Licensed under GNU GPLv3. See COPYING.txt for details.
from tornado.httpclient import HTTPRequest
from tornado.httputil import url_concat
from torwuf.controllers.testing import BaseTestCase
import base64
import http.client
import unittest


class TestBzr(BaseTestCase):
    def test_basic(self):
        self.http_client.fetch(self.get_url('/bzr/'), self.stop)
        response = self.wait()
        self.assertEqual(response.code, http.client.OK)

    def test_sequence(self):
        username = 'kitteh'
        password = 'shooZoh5'
        http_auth_key = 'Authorization'
        http_auth_value = 'Basic ' + str(base64.b64encode(
            bytes('{}:{}'.format(username, password), 'utf8')), 'utf8')

        self.http_client.fetch(HTTPRequest(
            url_concat(self.get_url('/bzr/user/create'),
                {'username': username, 'password': password,
                'password2': password}),
            method='POST',
            headers={http_auth_key: http_auth_value, }
            ),
            self.stop,
        )

        response = self.wait()
        self.assertEqual(response.code, http.client.OK)

        self.http_client.fetch(HTTPRequest(
            url_concat(self.get_url('/bzr/repo/create'),
                {'name': 'my_test_repo', }),
            method='POST',
            headers={http_auth_key: http_auth_value, },),
            self.stop
        )

        response = self.wait()
        self.assertEqual(response.code, http.client.OK)

        self.http_client.fetch(HTTPRequest(
            url_concat(self.get_url('/bzr/repo/my_test_repo'),
            {
                http_auth_key: http_auth_value,
            }),
            headers={http_auth_key: http_auth_value, },
            ),
            self.stop
        )

        response = self.wait()
        self.assertEqual(response.code, http.client.OK)

        self.http_client.fetch(HTTPRequest(
            url_concat('/bzr/repo/delete'),
            {'name': 'my_test_repo', 'mollyguard': 'deletion',
                http_auth_key: http_auth_value,
            },
            method='POST',
            headers={http_auth_key: http_auth_value, },
            ), self.stop)

        response = self.wait()
        self.assertEqual(response.code, http.client.OK)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
