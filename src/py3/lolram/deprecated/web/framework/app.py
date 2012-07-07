'''WSGI framework'''
#
#    Copyright © 2011-2012 Christopher Foo <chris.foo@gmail.com>
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
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
import configparser
import logging
import lolram.deprecated.web.tornado
import os.path
import string
import tempfile
import tornado.web
import urllib.parse
import warnings

_logger = logging.getLogger(__name__)


class Configuration(object):
    def __init__(self, config_parser, debug_mode=False):
        self._config_parser = config_parser
        self._root_path = config_parser['application']['root-path']
        self._debug_mode = debug_mode
        self._torando_settings = {'debug': debug_mode}

        self.read_config_file()
        self.create_db_dirs()

    @property
    def root_path(self):
        return self._root_path

    @property
    def debug_mode(self):
        return self._debug_mode

    @property
    def db_path(self):
        return self._db_path

    @property
    def upload_path(self):
        return self._upload_path

    @property
    def config_parser(self):
        return self._config_parser

    @property
    def tornado_settings(self):
        return self._torando_settings

    def read_config_file(self):
        if self._debug_mode:
            config_filename = 'app_debug.config'
        else:
            config_filename = 'app.config'

        config_parser = configparser.ConfigParser()
        config_path = os.path.join(self._root_path, config_filename)

        _logger.info('Configuration file path: %s', config_path)

        sucessful_files = config_parser.read([config_path])

        if sucessful_files:
            _logger.debug('Read %s configuration files', len(sucessful_files))
        else:
            _logger.warn('No configuration files read')

    def create_db_dirs(self):
        self._db_path = os.path.join(self.root_path, 'databases/')
        self._upload_path = os.path.join(self._db_path, 'uploads/')

        _logger.info('Database path: %s', self._db_path)

        if not os.path.exists(self._db_path):
            _logger.info('Creating path %s', self._db_path)
            os.makedirs(self._db_path)

        if not os.path.exists(self._upload_path):
            _logger.info('Creating path %s', self._upload_path)
            os.makedirs(self._upload_path)


class ApplicationController(object):
    def __init__(self, configuration, controller_classes):
        self._configuration = configuration

        self.init_database()
        self.init_url_specs(controller_classes)
        self.init_wsgi_application()

    @property
    def config(self):
        return self._configuration

    @property
    def wsgi_application(self):
        return self._wsgi_application

    @property
    def database(self):
        # database should probably be a controller
        return self._database

    @property
    def controllers(self):
        return self._controllers

    def init_url_specs(self, controller_classes):
        if not controller_classes:
            raise Exception('You must define at least one controller class')

        self._url_specs = []
        self._controllers = {}

        for controller_class in controller_classes:
            controller = controller_class(self)
            self._url_specs.extend(controller.url_specs)
            self._controllers[controller.__class__.__name__] = controller

    def init_wsgi_application(self):
        self._wsgi_application = lolram.deprecated.web.tornado.WSGIApplication(
            self._url_specs,
            **self.config.tornado_settings
        )

    def init_database(self):
        raise NotImplementedError()


class BaseController(object):
    def __init__(self, app_controller):
        self._app_controller = app_controller
        self._url_specs = []
        self.init()

    def init(self):
        pass

    @property
    def application(self):
        '''
        
        :deprecated:
            Use `app_controller`
        '''
        return self._app_controller

    @property
    def app_controller(self):
        return self._app_controller

    @property
    def config(self):
        return self._app_controller.config

    @property
    def controllers(self):
        return self._app_controller.controllers

    @property
    def url_specs(self):
        return self._url_specs

    def add_url_spec(self, url_pattern, handler_class, **handler_kargs):
        handler_kargs['controller'] = self

        url_spec = tornado.web.URLSpec(url_pattern, handler_class,
            handler_kargs, name=handler_class.name)
        self._url_specs.append(url_spec)


class BaseHandler(tornado.web.RequestHandler):
    name = NotImplemented

    @property
    def controller(self):
        return self._controller

    @property
    def app_controller(self):
        return self._controller.app_controller

    @property
    def controllers(self):
        return self._controller.controllers

    def initialize(self, controller, **kargs):
        self._controller = controller
        self.init(**kargs)

    def init(self, **kargs):
        pass

    def write(self, chunk):
        if not isinstance(chunk, bytes):
            warnings.warn('Automatically encoding str to bytes')
            chunk = chunk.encode()

        self._write_buffer.append(chunk)

    def flush(self, include_footers=False, callback=None):
        self.request.write(b''.join(self._write_buffer))
        self._write_buffer = []

    def finish(self, chunk=None):
        if chunk:
            if not isinstance(chunk, bytes):
                warnings.warn('Automatically encoding str to bytes')
                chunk = chunk.encode()

            self._write_buffer.append(chunk)

        self._compute_nonstreaming_headers()
        self._headers_written = True

        self.request.finish(b''.join(self._write_buffer))
        self._finished = True

    def _compute_nonstreaming_headers(self):
        # Automatically support ETags and add the Content-Length header if
        # we have not flushed any content yet.
        if not self._headers_written:
            if (self._status_code == 200 and
                self.request.method in ("GET", "HEAD") and
                "Etag" not in self._headers):
                etag = self.compute_etag()
                if etag is not None:
                    inm = self.request.headers.get("If-None-Match")
                    if inm and inm.find(etag) != -1:
                        self._write_buffer = []
                        self.set_status(304)
                    else:
                        self.set_header("Etag", etag)
            if "Content-Length" not in self._headers:
                content_length = sum(len(part) for part in self._write_buffer)
                self.set_header("Content-Length", content_length)
