#!/usr/bin/env python3

import argparse
import os
import os.path
import hashlib

def main():
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument('target_dir', type=str,
		metavar='TARGET_DIR', nargs='+')
	
	args = arg_parser.parse_args()
	hash_obj = hashlib.md5()
	
	for directory in args.target_dir:
		for path in sorted(get_paths(directory)):
			hash_obj.update(path.encode('utf8'))
		
			with open(path, 'rb') as f:
				data = f.read(4096)
			
				if data == b'':
					break
			
				hash_obj.update(data)
		
	print(hash_obj.hexdigest())

def get_paths(directory):
	for dirpath, dirnames, filenames in os.walk(directory):
		for dirname in list(dirnames):
			if dirname.startswith('.'):
				dirnames.remove(dirname)
				continue
			
		for filename in filenames:
			if not filename.startswith('.') and not filename.endswith('~'):
				yield os.path.join(dirpath, filename)

if __name__ == '__main__':
	main()
