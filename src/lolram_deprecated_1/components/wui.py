#encoding=utf8

'''Web-based user interface'''

#	Copyright © 2010–2011 Christopher Foo <chris.foo@gmail.com>

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
from lolram_deprecated_1.components import base
from lolram_deprecated_1.widgets import Document
import glob
import os


class WUI(base.BaseComponent):
	default_config = configloader.DefaultSectionConfig('wui',
		title_suffix='',
		optimize_scripts=True,
		optimize_styles=True,
		scripts_dir='scripts',
		styles_dir='styles',
	)
	
	HTML = 'html'
	
	def init(self):
		self._default_resources = []
		
		self.populate_resources()
	
	def setup(self):
		self._content_type = 'text/html'
		self._format = self.HTML
		self._content = None
	
	def render(self):
		# TODO: support other formats
		if self.context.exists(Document):
			global_wui = WUI(self.context.global_context)
			document = Document(self.context)
			document.resources.extend(global_wui._default_resources)
			self.context.response.set_content_type('text/html')
			return document.render(self.context, 'html')
	
	def populate_resources(self):
		global_wui = WUI(self.context.global_context)
		
		scripts_dir = self.context.config.wui.scripts_dir
		
		if scripts_dir:
			scripts_dir = os.path.join(self.context.dirinfo.www, scripts_dir)
			
			for p in glob.glob('%s/*.js' % scripts_dir):
				filename = p.replace(self.context.dirinfo.www, '')
				
				global_wui._default_resources.append(
					Document.Resource(Document.Resource.SCRIPT, filename)
				)
	
		styles_dir = self.context.config.wui.styles_dir
		if styles_dir:
			styles_dir = os.path.join(self.context.dirinfo.www, styles_dir)
			
			for p in glob.glob('%s/*.css' % styles_dir):
				filename = p.replace(self.context.dirinfo.www, '')
				
				global_wui._default_resources.append(
					Document.Resource(Document.Resource.STYLE, filename)
				)
	
#	def get_resources(self):
#		
#
#
#		
#		if not '_doc_scriptsstyles' in wui_component.singleton.__dict__:
#			styles = []
#			scripts = []
#			scripts_dir = self.context.config.wui.scripts_dir
#			if scripts_dir:
#				scripts_dir = os.path.join(self.context.dirinfo.www, scripts_dir)
#				
#				for p in glob.glob('%s/*.js' % scripts_dir):
#					filename = p.replace(self.context.dirinfo.www, '')
#					scripts.append(p)
#		
#			styles_dir = self.context.config.wui.styles_dir
#			if styles_dir:
#				styles_dir = os.path.join(self.context.dirinfo.www, styles_dir)
#				
#				for p in glob.glob('%s/*.css' % styles_dir):
#					filename = p.replace(self.context.dirinfo.www, '')
#					styles.append(p)
#			
#			wui_component.singleton._doc_scriptsstyles = (scripts, styles)
#		
#		scripts, styles = wui_component.singleton._doc_scriptsstyles
#		
#			




