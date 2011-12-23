#!/usr/bin/env python

import xmlrpclib
import sys
import urllib2
import shutil
import os.path

def main():
	pypi = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')
	third_party_dir = './third-party/'
	release_name = sys.argv[1]
	releases = pypi.package_releases(release_name)
	version = releases[0]
	dest_filename = os.path.join(third_party_dir, '%s-%s.zip' % (release_name, version))
	
	if not os.path.exists(dest_filename):
		downloads = pypi.release_urls(release_name, version)
		url = None
		
		for release_info in downloads:
			if release_info['packagetype'] == 'sdist':
				url = release_info['url']
				break
		
		if url:
			response_file = urllib2.urlopen(url)
		
			with open(dest_filename, 'wb') as dest_file:
				shutil.copyfileobj(response_file, dest_file)
		
		data_info_filename = os.path.join(third_party_dir, 
			'%s.version' % release_name)
		
		with open(data_info_filename, 'wb')  as f:
			f.write(version)
		
		if not url:
			sys.exit(1)

if __name__ == '__main__':
	main()
