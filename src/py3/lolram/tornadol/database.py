'''MongoDB database controller'''
#
# Copyright © 2012 Christopher Foo <chris.foo@gmail.com>
#
# This file is part of Lolram.
#
# Photon Vault is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Photon Vault is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Photon Vault.  If not, see <http://www.gnu.org/licenses/>.
#
from lolram.tornado import RequestHandlerMixin
from tornado.web import RequestHandler, URLSpec
import gridfs
import logging
import pymongo.connection
import queue
import threading
import time
import tornado.web

__docformat__ = 'restructuredtext en'


_logger = logging.getLogger(__name__)


class DatabaseDeferredExecutor(threading.Thread):
    def __init__(self, controller):
        threading.Thread.__init__(self)
        self.daemon = True
        self.name = 'DatabaseDeferredExecutor'
        self.controller = controller

    def run(self):
        while True:
            f = self.controller.queue.get(block=True, timeout=None)

            sleep_time = 1

            while True:
                try:
                    db = self.controller.db
                except pymongo.errors.AutoReconnect:
                    db = None

                if db:
                    _logger.debug('Executing database task %s', f)
                    f()
                    break

                _logger.debug('Database will sleep %s s before task %s',
                    sleep_time, f)
                time.sleep(sleep_time)
                sleep_time *= 2
                sleep_time = min(3600, sleep_time)


class DatabaseController(tornado.web.Controller):
    def get_handlers(self):

        if self.application.config_parser.has_option('database',
        'debug-allow-drop-all') and self.application.config_parser.getboolean(
        'database', 'debug-allow-drop-all'):
            return [URLSpec('/database/drop', DropHandler)]

        return []

    @classmethod
    def get_host_and_port(cls, config_parser):
        host = 'localhost'
        port = 27017

        if config_parser.has_option('database', 'host'):
            host = config_parser.get('database', 'host')

        if config_parser.has_option('database', 'port'):
            port = config_parser.getint('database', 'port')

        return (host, port)

    @classmethod
    def get_database_name(cls, config_parser):
        name = 'test'

        if config_parser.has_option('database', 'name'):
            name = config_parser.get('database', 'name')

        return name

    @classmethod
    def get_username_password(cls, config_parser):
        if config_parser.has_option('database', 'username'):
            host = config_parser.get('database', 'username')
            port = config_parser.getint('database', 'password')

            return (host, port)

        return (None, None)

    def init(self):
        self.queue = queue.Queue()
        self.host, self.port = DatabaseController.get_host_and_port(
            self.application.config_parser)
        self.connection = None
        self.deferred_executor = DatabaseDeferredExecutor(self)
        self.deferred_executor.start()
        self.name = DatabaseController.get_database_name(
            self.application.config_parser)
        self.username, self.password = DatabaseController\
            .get_username_password(self.application.config_parser)

    @property
    def db(self):
        if not self.connection:
            self.connection = pymongo.connection.Connection(self.host,
                self.port)

        c = self.connection[self.name]

        if self.username:
            c.authenticate(self.username, self.password)

        return c

    @property
    def fs(self):
        return gridfs.GridFS(self.db)

    def execute_when_ready(self, func):
        self.queue.put(func)


class DropHandler(RequestHandler, RequestHandlerMixin):
    def get(self):
        db = self.controllers[DatabaseController].db

        for name in db.collection_names():
            if not name.startswith('system'):
                db.drop_collection(name)

        self.finish()
