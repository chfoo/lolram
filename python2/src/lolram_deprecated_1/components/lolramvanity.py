# encoding=utf8

'''Lolram vanity'''

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

from lolram_deprecated_1.components import base
import lolram_deprecated_1

__docformat__ = 'restructuredtext en'

class LolramVanity(base.BaseComponent):
	def setup(self):
		if self.context.response:
			self.context.response.headers['X-Script'] = 'lolram/%s' % lolram_deprecated_1.app.__version__

	
