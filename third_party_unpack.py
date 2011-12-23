#!/usr/bin/env python

import sys
import os.path
import subprocess
import os

def main():
	package_name = sys.argv[1]
	third_party_dir = './third-party/'
	
	with open(os.path.join(third_party_dir, '%s.version' % package_name)) as f:
		version = f.read()
	
	filename_tar = os.path.abspath(os.path.join(third_party_dir, '%s-%s.tar.gz' % (package_name, version)))
	filename_zip = os.path.abspath(os.path.join(third_party_dir, '%s-%s.zip' % (package_name, version)))
	
	os.chdir(third_party_dir)
	
	if os.path.exists(filename_tar):
		proc = subprocess.Popen(['tar', '-xzf', filename_tar,])
		proc.wait()
		sys.exit(proc.returncode)
	
	if os.path.exists(filename_zip):
		proc = subprocess.Popen(['unzip', '-o', filename_zip,])
		proc.wait()
		sys.exit(proc.returncode)
	
	sys.exit(1)
	
if __name__ == '__main__':
	main()


