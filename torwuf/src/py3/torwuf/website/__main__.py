'''Starts up a server'''
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
from torwuf.website.app import Application
import argparse
import configparser
import glob
import subprocess
import threading
import tornado.ioloop
import torwuf.website.main


class LegacyAppLauncher(threading.Thread):
    def __init__(self, args):
        threading.Thread.__init__(self)
        self.name = 'legacy_app'
        self.daemon = True
        self.args = args

    def run(self):
        p = subprocess.Popen(['python3'] + self.args)
        p.wait()


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--config', metavar='FILE',
        default='/etc/torwuf/torwuf2.conf',
        dest='config')
    arg_parser.add_argument('--config-glob', metavar='PATTERN',
        default='/etc/torwuf/torwuf2.*.conf',
        dest='config_glob')
    arg_parser.add_argument('--legacy-args',
        default='',
        dest='legacy_args')

    args = arg_parser.parse_args()

    legacy_app = LegacyAppLauncher(args.legacy_args.split())
    legacy_app.start()

    config_parser = configparser.ConfigParser()
    config_parser.read([args.config] + \
        glob.glob(args.config_glob))

    torwuf.website.main.configure_logging(config_parser, 'torwuf2')

    application = Application(config_parser)

    application.listen(config_parser.getint('server', 'port'),
        config_parser.get('server', 'address'))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
