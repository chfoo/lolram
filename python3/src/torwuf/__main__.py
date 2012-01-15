import argparse
import configparser
import flup.server.fcgi
import logging
import logging.handlers
import lolram.web.wsgi
import os
import os.path
import torwuf.web.controllers.app
import wsgiref.simple_server
import torwuf.web.utils

def main():
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument('--config', metavar='FILE',
		default='/etc/torwuf/torwuf.conf',
		dest='config')
	args = arg_parser.parse_args()
	
	config_parser = configparser.ConfigParser()
	sucessful_files = config_parser.read([args.config])
	
	if not sucessful_files:
		raise Exception('Configuration file %s not found' % args.config)
	
	configure_logging(config_parser)
	application, server = configure_application(config_parser)
	
	if hasattr(server, 'run'):
		server.run()
	else:
		server.serve_forever()

def configure_application(config_parser):
	server_method = config_parser['server']['method']
	root_path = config_parser['application']['root-path']
	application = torwuf.web.controllers.app.Application(root_path)
	
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
		logger.setLevel(logging.INFO)
		handler = logging.handlers.RotatingFileHandler('%s/torwuf' % log_dir,
			maxBytes=4194304, backupCount=10)
		logger.addHandler(handler)

if __name__ == '__main__':
	main()
