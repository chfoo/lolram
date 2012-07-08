'''Test the bzr controller'''
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
import base64
import http.client
import torwuf.deprecated.tests.web.server_base
import unittest


class TestBzr(unittest.TestCase,
torwuf.deprecated.tests.web.server_base.ServerBaseMixIn):
    def setUp(self):
        self.create_app()
        self.start_server()

    def tearDown(self):
        self.stop_server()

    def test_basic(self):
        response = self.request('/bzr/')
        self.assertEqual(response.status, http.client.OK)

    def test_sequence(self):
        username = 'kitteh'
        password = 'shooZoh5'
        http_auth_key = 'Authorization'
        http_auth_value = 'Basic ' + str(base64.b64encode(
            bytes('{}:{}'.format(username, password), 'utf8')), 'utf8')

        response = self.request('/bzr/user/create', method='POST',
            query_map={'username': username, 'password': password,
            'password2': password},
            headers={http_auth_key: http_auth_value, },
        )
        self.assertEqual(response.status, http.client.OK)

        response = self.request('/bzr/repo/create', method='POST',
            query_map={'name': 'my_test_repo', },
            headers={http_auth_key: http_auth_value, },
        )
        self.assertEqual(response.status, http.client.OK)

        response = self.request('/bzr/repo/my_test_repo',
            query_map={
                http_auth_key: http_auth_value,
            },
            headers={http_auth_key: http_auth_value, },
        )
        self.assertEqual(response.status, http.client.OK)

        response = self.request('/bzr/repo/delete', method='POST',
            query_map={'name': 'my_test_repo', 'mollyguard': 'deletion',
                http_auth_key: http_auth_value,
            },
            headers={http_auth_key: http_auth_value, },
        )
        self.assertEqual(response.status, http.client.OK)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
