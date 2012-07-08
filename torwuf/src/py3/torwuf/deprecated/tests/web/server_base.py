'''server mixin for testing'''
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
import configparser
import lolram.deprecated.tests.server_base
import lolram.deprecated.web.framework.app
import lolram.deprecated.web.wsgi
import os.path
import tempfile
import torwuf.web.controllers.app


class ServerBaseMixIn(lolram.deprecated.tests.server_base.ServerBaseMixIn):
    namespace = 'torwuf'

    def create_app(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_path = self.temp_dir.name
        config_parser = configparser.ConfigParser()

        config_filepath = os.path.join(os.path.dirname(__file__),
            'server.conf')
        sucessful_files = config_parser.read(config_filepath)

        if not sucessful_files:
            raise Exception(
                'No config file read. (tried %s)' % config_filepath)

        config_parser['application']['root-path'] = self.root_path
        configuration = lolram.deprecated.web.framework.app.Configuration(
            config_parser, debug_mode=True)
        self.app_wrapper = torwuf.web.controllers.app.Application(
            configuration)
        self.app = lolram.deprecated.web.wsgi.DecodeFromLatin1ToUnicode(
            self.app_wrapper.wsgi_application)
        self.config_parser = config_parser

    def request(self, path, method='GET', headers={}, query_map={}, data={},
    host=None, port=None):
        headers.update({
            'Testing-Key': self.config_parser['account']['testing_key']
        })

        return lolram.deprecated.tests.server_base.ServerBaseMixIn.request(
            self, path, method,
            headers, query_map, data, host, port)
