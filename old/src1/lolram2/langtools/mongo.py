# encoding=utf8

'''Language tools with MongoDB backend'''

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

import lolram2.langtools

class LangTool(object):
	COLLECTION_UNIHAN = 'unihan'	
	
	def set_database(self, db):
		self._db = db

	def lookup_unihan(self, c):
		return self._db[LangTool.COLLECTION_UNIHAN].find_one({'_id': c})
			

lolram2.langtools.LangTool.register(LangTool)
