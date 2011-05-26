# encoding=utf8

'''Base component'''

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

__doctype__ = 'restructuredtext en'

import imp


class BaseComponentManager(object):
	default_config = None
	agent_class = None
	name = NotImplemented
	
	def __init__(self, fardel):
		pass
	
class BaseComponentAgent(object):
	def __init__(self, fardel, manager):
		pass
		
	def setup(self, fardel):
		pass
	
	def control(self, fardel):
		pass
	
	def render(self, fardel):
		pass
	
	def cleanup(self, fardel):
		pass
	

