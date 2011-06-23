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

import base

class LionAgent(base.BaseComponentAgent):
	def setup(self, fardel):
		self._accepted_languages = []
		self._current_language = ('en', None)
		header = fardel.req.headers.get_first('Accept-Language')
		if header:
			l = header.value.split(',')
			for i in l:
				lang, a, locale = i.partition('_')
				self._accepted_languages.append((lang, locale))
	
	@property
	def current_language(self):
		return self._current_language
	
	def set_current_language(self, lang, locale=None):
		self._current_language = (lang, locale)
	
	@property
	def accepted_languages(self):
		return self._accepted_languages
	

class LionManager(base.BaseComponentManager):
	name = 'lion'
	agent_class = LionAgent
	