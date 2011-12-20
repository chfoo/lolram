#encoding=utf8

'''Website navigation support'''

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

import cStringIO

import tornado.web

class NavigationMixIn(object):
	'''A navigation RequestHandler mix-in'''
	
	def prepare(self):
		self._nav_model = Navigation()
	
	@property
	def navigation(self):
		return self._nav_model
	
#	def update_render_kargs(self, kargs):
#		kargs['nav'] = self.nav
		

class Navigation(list):
	def add(self, label, url, icon=None):
		self.append((label, url, icon))


class NavigationUIModel(tornado.web.UIModule):
	def render(self, nav=None):
		if nav is None:
			nav = self.handler.navigation
			
		buf = cStringIO.StringIO()
		
		buf.write('<nav class="navigationModule">')
		
		if not nav:
			buf.write('&nbsp;')
		
		for label, url, icon in nav:
			buf.write('<a href="')
			buf.write(tornado.escape.xhtml_escape(url))
			buf.write('">')
			buf.write(tornado.escape.xhtml_escape(label))
			buf.write('</a>')
		
		buf.write('</nav>')
		buf.seek(0)
		
		return buf.read()