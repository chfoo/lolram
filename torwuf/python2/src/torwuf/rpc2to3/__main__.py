#!/usr/bin/env python

import ConfigParser
import argparse
import glob
import torwuf.rpc2to3.rpcserver

def main():
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument('--config', metavar='FILE',
		default='/etc/torwuf/torwuf.conf',
		dest='config')
	arg_parser.add_argument('--config-glob', metavar='PATTERN',
		default='/etc/torwuf/torwuf.*.conf',
		dest='config_glob')
	args = arg_parser.parse_args()
	
	config_parser = ConfigParser.ConfigParser()
	sucessful_files = config_parser.read([args.config] + \
		glob.glob(args.config_glob))
	
	if not sucessful_files:
		raise Exception('Configuration file %s not found' % args.config)
	
	server = torwuf.rpc2to3.rpcserver.make_server(
		config_parser.get('rpc2to3', 'address'), 
		config_parser.getint('rpc2to3', 'port'),
		config_parser)
	
	server.serve_forever()

if __name__ == '__main__':
	main()