# encoding=utf8

'''Pagination utilities'''

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

class PageInfo(object):
	def __init__(self, page=1, offset=0, limit=100, max_item=None, more=False):
		self.page = max(1, int(page))
		self.offset = offset
		self.limit = limit
		self.max_item = max_item
		self.more = more
	
	def get_page_numbers(self, current=None):
		current = current or self.page
		
		l = [1]
		
		l.extend(range(max(2, current - 3), current + 1))
		
		if self.more and not self.max_item:
			l.append(current + 1)
		elif self.offset < self.max_item:
			max_page = self.max_item // self.limit + 1
			l.extend(range(current + 1, min(max_page - 1, current + 3)))
			l.append(max_page)
		
		return l
			