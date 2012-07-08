'''The main application controller'''
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
import lolram.tornado
import tornado.web

__docformat__ = 'restructedtext en'


class Application(tornado.web.Application, lolram.tornado.ApplicationMixin):
    def __init__(self, config_parser):
        self._config_parser = config_parser
        tornado.web.Application.__init__(self)
        lolram.tornado.ApplicationMixin.__init__(self)

    @property
    def config_parser(self):
        return self._config_parser
