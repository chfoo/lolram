'''WSGI application testing'''
#
#    Copyright © 2011 Christopher Foo <chris.foo@gmail.com>
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
import gzip
import io
import lolram.deprecated.web.wsgi
import unittest
import wsgiref.util


class SimpleAppServerBase(unittest.TestCase):
    def setUp(self):
        self.environ = {}
        self.response_file = io.BytesIO()
        self.response_headers = None

        wsgiref.util.setup_testing_defaults(self.environ)

        def start_response(status, response_headers, exc_info=None):
            self.response_headers = response_headers
            return self.response_file

        self.start_response = start_response

    def write_into_response_file(self, iterator):
        for v in iterator:
            self.response_file.write(v)

    def seek_files_to_zero(self):
        self.response_file.seek(0)


class TestCompressor(SimpleAppServerBase):
    BINARY_APP_DATA = b'X' * 100
    TEXT = 'Stochastic Ruby Dragon⁓'.encode()

    def setUp(self):
        SimpleAppServerBase.setUp(self)
        self.environ['HTTP_ACCEPT_ENCODING'] = 'gzip'

    @staticmethod
    def binary_finite_app(environ, start_response):
        headers = [('Content-Length', '10000'),
            ('Content-Type', 'application/x-binary')]

        start_response('200 OK', headers)

        for i in range(10): #@UnusedVariable
            yield b'X' * 10

    @staticmethod
    def binary_streaming_app(environ, start_response):
        headers = [('Content-Type', 'application/x-binary'), ]

        start_response('200 OK', headers)

        for i in range(10): #@UnusedVariable
            yield b'X' * 10

    @staticmethod
    def text_finite_app(environ, start_response):
        headers = [('Content-Length', str(len(TestCompressor.TEXT))),
            ('Content-Type', 'text/plain; encoding=utf-8'),
            ]

        start_response('200 OK', headers)

        return (v for v in (TestCompressor.TEXT[:5], TestCompressor.TEXT[5:]))

    @staticmethod
    def text_streaming_app(environ, start_response):
        headers = [('Content-Type', 'text/plain; encoding=utf-8'), ]

        start_response('200 OK', headers)

        return (v for v in (TestCompressor.TEXT[:5], TestCompressor.TEXT[:5]))

    @staticmethod
    def large_payload_app(environ, start_response):
        text = b'x' * 10000000
        headers = [('Content-Length', str(len(text))),
            ('Content-Type', 'text/plain; encoding=utf-8'),
            ]

        start_response('200 OK', headers)

        return [text]

    @staticmethod
    def large_streaming_payload_app(environ, start_response):
        text = b'x' * 10000000
        headers = [
            ('Content-Type', 'text/plain; encoding=utf-8'),
            ]

        start_response('200 OK', headers)

        return [text]

    def test_uncompressable_finite_binary(self):
        '''It should leave the response untouched'''

        compressor_app = lolram.deprecated.web.wsgi.Compressor(TestCompressor.binary_finite_app)

        self.write_into_response_file(compressor_app(self.environ, self.start_response))
        self.seek_files_to_zero()
        self.assertEquals(TestCompressor.BINARY_APP_DATA, self.response_file.read())

    def test_uncompressable_streaming_binary(self):
        '''It should leave the response untouched'''

        compressor_app = lolram.deprecated.web.wsgi.Compressor(TestCompressor.binary_streaming_app)

        self.write_into_response_file(compressor_app(self.environ, self.start_response))
        self.seek_files_to_zero()
        self.assertEquals(TestCompressor.BINARY_APP_DATA, self.response_file.read())

    def test_compressable_finite_text(self):
        '''It should compress the text'''

        compressor_app = lolram.deprecated.web.wsgi.Compressor(TestCompressor.text_finite_app)

        self.write_into_response_file(compressor_app(self.environ, self.start_response))
        self.seek_files_to_zero()
        self.assertIn(('Content-Encoding', 'gzip'), self.response_headers)
        self.assertEquals(TestCompressor.TEXT, gzip.decompress(self.response_file.read()))

    def test_large_finite_payload(self):
        '''It should not compress the large payload if it is not streamed'''

        compressor_app = lolram.deprecated.web.wsgi.Compressor(TestCompressor.large_payload_app)

        self.write_into_response_file(compressor_app(self.environ, self.start_response))
        self.seek_files_to_zero()
        self.assertEquals(b'x' * 10000000, self.response_file.read())

    def test_large_streaming_payload(self):
        '''It should compress the large payload if it is streamed'''

        compressor_app = lolram.deprecated.web.wsgi.Compressor(TestCompressor.large_streaming_payload_app)

        self.write_into_response_file(compressor_app(self.environ, self.start_response))
        self.seek_files_to_zero()

        response = self.response_file.read()

        print('size', len(response))

        self.assertIn(('Content-Encoding', 'gzip'), self.response_headers)
        self.assertEquals(b'x' * 10000000, gzip.decompress(response))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
