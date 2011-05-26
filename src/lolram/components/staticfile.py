# encoding=utf8

'''Static File'''

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

import os

import base
from .. import configloader
from .. import urln11n

class StaticFileAgent(base.BaseComponentAgent):
	def __init__(self, fardel, manager):
		self._fardel = fardel
	
	def control(self, fardel):
		if fardel.req.controller == fardel.conf.static_file.path_name:
			fardel.resp.ok()
			return fardel.resp.output_file(
				os.path.join(fardel.dirs.www, 
					urln11n.collapse_path('/'.join(fardel.req.args))))
	
	@property
	def name(self):
		return self._fardel.conf.static_file.path_name

class StaticFileManager(base.BaseComponentManager):
	default_config = configloader.DefaultSectionConfig('static_file',
		path_name='zf',
	)
	name = 'static_file'
	agent_class = StaticFileAgent


