#!/usr/bin/env python

import sys
import os.path
import subprocess

def main():
	package_name = sys.argv[1]
	third_party_dir = './third-party/'
	
	with open(os.path.join(third_party_dir, '%s.version' % package_name)) as f:
		version = f.read()
	
	filename = os.path.join(third_party_dir, '%s-%s.zip' % (package_name, version))
	
	proc = subprocess.Popen(['unzip', '-f', filename,])
	proc.wait()
	
if __name__ == '__main__':
	main()


