'''Starts up a server'''
#
#	Copyright (c) 2012 Christopher Foo <chris.foo@gmail.com>
#
#	This file is part of Torwuf.
#
#	Torwuf is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	Torwuf is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with Torwuf.  If not, see <http://www.gnu.org/licenses/>.
#
import argparse
import configparser
import flup.server.fcgi
import glob
import logging
import logging.handlers
import lolram.web.framework.app
import lolram.web.wsgi
import os
import os.path
import subprocess
import threading
import torwuf.web.controllers.app
import torwuf.web.utils
import wsgiref.simple_server

def main():
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument('--config', metavar='FILE',
		default='/etc/torwuf/torwuf.conf',
		dest='config')
	arg_parser.add_argument('--config-glob', metavar='PATTERN',
		default='/etc/torwuf/torwuf.*.conf',
		dest='config_glob')
	arg_parser.add_argument('--debug-mode', default=False, action='store_true',
		dest='debug_mode')
	arg_parser.add_argument('--rpc-server', default=False, action='store_true', 
		dest='rpc_server')
	arg_parser.add_argument('--python-2-path', dest='python_2_path')
	args = arg_parser.parse_args()
	
	config_parser = configparser.ConfigParser()
	sucessful_files = config_parser.read([args.config] + \
		glob.glob(args.config_glob))
	
	if not sucessful_files:
		raise Exception('Configuration file %s not found' % args.config)
	
	configure_logging(config_parser)
	application, server = configure_application(config_parser, args.debug_mode)
	
	if args.rpc_server:
		run_rpc_server(args.python_2_path, args.config, args.config_glob)
	
	if hasattr(server, 'run'):
		server.run()
	else:
		server.serve_forever()

def configure_application(config_parser, debug_mode=False):
	server_method = config_parser['server']['method']
	
	configuration = lolram.web.framework.app.Configuration(config_parser,
		debug_mode=debug_mode)
	application = torwuf.web.controllers.app.Application(configuration)
	
	if server_method == 'fastcgi':
		path = config_parser['server']['path']
		wsgi_application = torwuf.web.utils.StripDummyAppPath(
			application.wsgi_application)
		server = flup.server.fcgi.WSGIServer(wsgi_application,
			bindAddress=path, umask=0o111)
		
	elif server_method == 'host':
		address = config_parser['server']['address']
		port = int(config_parser['server']['port'])
		server = wsgiref.simple_server.make_server(address, port,
			application.wsgi_application)
	
	if config_parser['application'].getboolean('compress'):
		application = lolram.web.wsgi.Compressor(application)
	
	return (application, server)

def configure_logging(config_parser):
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
		
		handler = logging.handlers.RotatingFileHandler('%s/torwuf' % log_dir,
			maxBytes=4194304, backupCount=10)
		logger.addHandler(handler)
		handler.setFormatter(logging.Formatter('%(asctime)s '+
			'%(name)s:%(module)s:%(lineno)d:%(levelname)s %(message)s'))

def run_rpc_server(path, config_path, config_glob_path):
	env = os.environ.copy()
	# We don't want to mix python 3 paths, so we clear it 
	env['PYTHONPATH'] = path
	
	def runner():
		p = subprocess.Popen(['python', '-m', 'torwuf.rpc2to3', '--config', 
			config_path, '--config-glob', config_glob_path],
			env=env
		)
		p.wait()
	
	thread = threading.Thread(target=runner)
	thread.daemon = True
	thread.start()

if __name__ == '__main__':
	main()
