'''Testing'''
#
#	Copyright (c) 2012 Christopher Foo <chris.foo@gmail.com>
#
#	This file is part of Torwuf.
#
#	Torwuf is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	Torwuf is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with Torwuf.  If not, see <http://www.gnu.org/licenses/>.
#
import torwuf.web.controllers.base


class TestController(torwuf.web.controllers.base.BaseController):
	def init(self):
		self.add_url_spec('/test/unicodeð', UnicodeHandler)
		self.add_url_spec('/test/unicode😸', UnicodeHandler)
		
		
class UnicodeHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'test_unicode'
	
	def get(self):
		self.write('ok')