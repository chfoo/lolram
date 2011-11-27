# encoding=utf8

'''Language tools'''

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

import abc

import nltk

class LangTool(object):
	__metaclass__ = abc.ABCMeta
	
	PHONETIC_IPA = 'ipa'
	
	
	
	def transcribe(self, s, orthographic=None, phonetic=PHONETIC_IPA, 
	gloss=True, compounds=True,):
		assert isinstance(s, unicode)
		
		for word in nltk.word_tokenize(s):
			if len(word) == 1:
				result = self.lookup_unihan(word)
			
				if result:
					
	
	@abc.abstractmethod
	def lookup_unihan(self, c):
		pass
	
	def split_jyutping(self, c):
		



