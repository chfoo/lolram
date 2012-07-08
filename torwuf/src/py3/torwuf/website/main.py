'''Server initialization procedures'''
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
import logging
import os.path

__docformat__ = 'restructuredtext en'


def configure_logging(config_parser, namespace='torwuf'):
    root_path = config_parser['application']['root-path']
    log_dir = os.path.join(root_path, 'logs')

    def create_log_dir():
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

    if config_parser['logging'].getboolean('enable'):
        create_log_dir()

        logging.captureWarnings(True)
        logger = logging.getLogger()

        if config_parser['logging'].getboolean('debug'):
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, namespace),
            maxBytes=4194304, backupCount=10)
        logger.addHandler(handler)
        handler.setFormatter(logging.Formatter('%(asctime)s ' \
            '%(name)s:%(module)s:%(lineno)d:%(levelname)s %(message)s'))
