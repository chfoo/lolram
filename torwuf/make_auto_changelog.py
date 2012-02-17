#!/usr/bin/env python3

import argparse
import os
import os.path
import subprocess
import datetime

def main():
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument('package_names', type=str,
		metavar='PACKAGE_NAME', nargs='+')
	arg_parser.add_argument('--source-package', dest='source_package',
		required=True)
	
	args = arg_parser.parse_args()
	major_version = open('VERSION', 'r').read().strip()
	
	for package_name in args.package_names:
		print('Package', package_name)
	
		change_hash_filename = '.change_hash.%s' % package_name
		
		if os.path.exists(change_hash_filename):
			old_hash = open(change_hash_filename, 'r').read().strip().lower()
		else:
			old_hash = None
		
		p = subprocess.Popen(['./calc_hash.py', 'debian/%s' %package_name],
			stdout=subprocess.PIPE)
		out, err = p.communicate()
		new_hash = str(out, 'utf8').strip().lower()
		
		if old_hash != new_hash:
			print('New changelog')
		
			date_obj = datetime.datetime.utcnow()
			date_string = '%(y)04d%(m)02d%(d)02d%(H)02d%(M)02d%(S)02d' % {
				'y': date_obj.year,
				'm': date_obj.month,
				'd': date_obj.day,
				'H': date_obj.hour,
				'M': date_obj.minute,
				'S': date_obj.second,
			}
			
			if os.path.exists('debian/%s.changelog' % package_name):
				os.remove('debian/%s.changelog' % package_name)
			
			p = subprocess.Popen(['debchange', '--changelog', 
				'debian/%s.changelog' % package_name, '--preserve',
				'--newversion', '%s-upstream%s' % (major_version, date_string),
				'--distribution', 'UNRELEASED', '--force-distribution',
				'Scripted build', '--create',  '--package', args.source_package])
			p.wait()
		
			with open(change_hash_filename, 'w') as f:
				f.write(new_hash)
	
if __name__ == '__main__':
	main()

	
	
