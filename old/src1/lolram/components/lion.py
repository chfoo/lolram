#encoding=utf8

'''I18N and L10N'''

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

import babel.support

import base

class Lion(base.BaseComponent):
	def setup(self):
		self._acceptable_locales = []
		self._locale = 'en'
		self._formatter = babel.support.Format(self._locale)
		
		header = self.context.request.headers.get_first('Accept-Language')
		
		if header:
			l = header.value.split(',')
			
			for i in l:
				s = i.split(';')[0].strip().replace('-', '_')
				self._acceptable_locales.append(s)
			
			if self._acceptable_locales:
				self._locale = self._acceptable_locales[0]
				self._formatter = babel.support.Format(self._locale)
	
	@property
	def locale(self):
		return self._locale
	
	@locale.setter
	def locale(self, s):
		self._locale = s
	
	@property
	def acceptable_locales(self):
		return self._acceptable_locales
	
	def t(self, s):
		return s
	
	@property
	def formatter(self):
		return self._formatter