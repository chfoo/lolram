#!/usr/bin/env python
#encoding=utf8

'''WSGI Executable Application'''

#	Copyright © 2010–2011 Christopher Foo <chris.foo@gmail.com>

#	This file is part of Lolram.

#	Lolram is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.

#	Lolram is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.

#	You should have received a copy of the GNU General Public License
#	along with Lolram.  If not, see <http://www.gnu.org/licenses/>.

__docformat__ = 'restructuredtext en'

import optparse
import os
import sys
from wsgiref.simple_server import make_server
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(p)

import flup.server.fcgi

from lolram_deprecated_1 import app
from lolram_deprecated_1 import mylogger

logger = mylogger.get_logger()

if __name__ == '__main__':
	option_parser = optparse.OptionParser()
	option_parser.add_option('-s', '--socket', dest='socket', 
		help='The Unix socket address in which to bind with',
		default='/tmp/lolram.socket')
	option_parser.add_option('-c', '--conf', dest='conf', 
		help='The PATH of the configuration file',
		default='site.conf')
	option_parser.add_option('-l', '--logfile', dest='logfile',
		help='The PATH of log file')
	option_parser.add_option('-p', '--port', dest='port',
		help='The TCP port used to bind the server')
	
	options, args = option_parser.parse_args()
	
	if options.logfile:
		logger.addHandler(mylogger.file_handler(options.logfile))
	
	logger.info('Running as executable')
	
	logger.debug(os.environ)
	logger.debug(sys.argv)
	
	if options.port:
#		app = validator(app.WSGIApp(options.conf))
		# XXX: Validator does not support length for readlines
		app = app.WSGIApp(options.conf)
		httpd = make_server('', int(options.port), app)
		httpd.serve_forever()
	else:
		socket_name = options.socket
	
		# FIXME: lighttpd can spawn more than 1 process, need to get the new socket 
		# name because it appends -N where N is a number from 0.
	#	# This is only true if lighttpd is responsible for spawning the process 
		#if socket_name and 'PHP_FCGI_CHILDREN':
	#		socket_name += int(os.environ['PHP_FCGI_CHILDREN']) - 1 # 0 base it
	#	
		logger.debug('Socket name %s', socket_name)
	
		flup.server.fcgi.WSGIServer(app.WSGIApp(options.conf),
			bindAddress=socket_name).run()
		logger.info('Finished running as executable')
