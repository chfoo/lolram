#!/usr/bin/env python
# encoding=utf8

'''GDBM utilities including import/export'''

#	Copyright © 2011 Christopher Foo <chris.foo@gmail.com>

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

import contextlib
import time
import gdbm
import csv
import argparse
import sys

class LockError(Exception):
	pass

@contextlib.contextmanager
def connection(filename, flag='r', mode=0666, sync=True, timeout=5):
	start_time = time.time()
	
	while True:
		if abs(time.time() - start_time) > timeout:
			raise LockError()
		
		try:
			db_ = gdbm.open(filename, flag, mode)
			break
		except gdbm.error, e:
			if e.message.lower().index('lock') != -1:
				time.sleep(0.1)
			else:
				raise e
			
	yield db_
	
	if sync:
		db_.sync()
	db_.close()

def import_csv(f, db):
	reader = csv.reader(f)
	
	for row in reader:
		db[row[0]] = row[1]

def export_csv(db, f):
	key = db.firstkey()
	writer = csv.writer(f)
	
	while key is not None:
		writer.writerow([key, db[key]])
		key = db.nextkey(key)

def main():
	parser = argparse.ArgumentParser(description='Import and export GDBM files.',
		epilog='GDBM reading of files will fail if the file is from another architecture such as 32- and 64-bit machines.')
	parser.add_argument('command', metavar='COMMAND', type=str, nargs=1,
		help='export or import')
	parser.add_argument('db', metavar='DATABASE', type=str, nargs=1,
		help='Database file path')
	parser.add_argument('csvfile', metavar='CSVFILE', type=str, nargs='?',
		help='CSV file path (default: read/write from stdin or stdout')
	
	args = parser.parse_args()
	
	command = args.command[0]
	
	if command == 'export':
		if args.csvfile:
			csv_file = open(args.csvfile[0], 'wb')
		else:
			csv_file = sys.stdout 
		
		with connection(args.db[0]) as db:
			export_csv(db, csv_file)
		
		csv_file.flush()
	
	elif command == 'import':
		if args.csvfile:
			csv_file = open(args.csvfile[0], 'rb')
		else:
			csv_file = sys.stdin 
		
		with connection(args.db[0], 'cf') as db:
			import_csv(db, csv_file)
	
	else:
		print 'Unrecognized command. Use "import" or "export"'
		sys.exit(1)

if __name__ == '__main__':
	main()