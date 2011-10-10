# encoding=utf8

'''Support for MongoDB'''

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

__docformat__ = 'restructuredtext en'

import pymongo


class DatabaseMixIn(object):
	'''MongoDB database support mix-in class for Tornado RequestHandler'''
	
	def initialize(self, mongodb):
		self._mongodb = mongodb
	
	@property
	def db(self):
		return self._mongodb


def get_database(database, username=None, password=None):
	connection = pymongo.Connection()
	database = connection[database]
		
	if username:
		database.authenticate(username, password)
	
	return database