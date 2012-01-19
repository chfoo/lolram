'''Basic DBM-style for json-serializable data in sqlite3 database'''
#
#	Copyright © 2012 Christopher Foo <chris.foo@gmail.com>
#
#	This file is part of Lolram.
#
#	Lolram is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	Lolram is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with Lolram.  If not, see <http://www.gnu.org/licenses/>.
#
import collections
import json
import sqlite3

__docformat__ = 'restructuredtext en'


class Database(collections.MutableMapping):
	def __init__(self, path, *sqlite_args, **sqlite_kargs):
		self.db = sqlite3.connect(path, *sqlite_args, **sqlite_kargs)

		with self.db as connection:
			connection.execute('CREATE TABLE IF NOT EXISTS '
				't(k TEXT PRIMARY KEY, v TEXT)'
			)
	
	def __len__(self):
		cursor = self.db.execute('SELECT SUM(1) FROM t')
		row = cursor.fetchone()
		
		if row and row[0]:
			return int(row[0])
		else:
			return 0
	
	def keys(self):
		return list(self.__iter__())
	
	def __iter__(self):
		cursor = self.db.execute('SELECT k FROM t')
		
		for row in cursor:
			yield row[0]
	
	def __getitem__(self, k):
		cursor = self.db.execute('SELECT v FROM t WHERE k = ?', [k])
		row = cursor.fetchone()
		
		if row:
			return json.loads(row[0])
		else:
			raise IndexError()
	
	def __contains__(self, k):
		try:
			self[k]
			return True
		except IndexError:
			return False
	
	def __setitem__(self, k, v):
		with self.db as connection:
			connection.execute('INSERT OR REPLACE INTO t (k, v) '
				'VALUES ( ?, ? )', [k, json.dumps(v)])
	
	def __delitem__(self, k):
		with self.db as connection:
			connection.execute('DELETE FROM t WHERE k = ? ', [k])
	
	def update(self, k, v):
		d = self[k]
		d.update(v)
		self[k] = d