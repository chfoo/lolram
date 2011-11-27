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

__docformat__ = 'restructuredtext en'

from lolram_deprecated_1 import configloader
import base
import lolram.util.url
import os


class StaticFile(base.BaseComponent):
	default_config = configloader.DefaultSectionConfig('static_file',
		path_name='zf',
	)

	def control(self):
		if self.context.request.controller == unicode(self.context.config.static_file.path_name):
			self.context.response.ok()
			return self.context.response.output_file(
				os.path.join(self.context.dirinfo.www, 
					lolram.util.url.collapse_path('/'.join(self.context.request.args))))
	
	@property
	def name(self):
		return self.context.config.static_file.path_name


