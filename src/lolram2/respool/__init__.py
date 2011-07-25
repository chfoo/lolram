# encoding=utf8

'''Resource pooling system

The resource pool system stores a single copy of strings or files and returns
an unique
ID number for the given resource.
'''

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


class TextResource(unicode):
	__slots__ = ('hash', 'id')


class FileResource(file):
	__slots__ = ('hash', 'filename', 'id')


class TextResPool(object):
	__metaclass__ = abc.ABCMeta
	
	@abc.abstractmethod
	def get_text(self, id):
		'''Get text by numeric id (`int` or `long`)
		
		:rtype: `TextResource`
		'''
		raise NotImplementedError()
	
	@abc.abstractmethod
	def set_text(self, text, create=True):
		'''Set text
		
		:parameters:
			create : `bool`
				If `False`, don't add the text to the database and return
				`None`
		
		:rtype: `int`
		'''
		raise NotImplementedError()


class FileResPool(object):
	__metaclass__ = abc.ABCMeta
	
	@abc.abstractmethod
	def get_file(self, id):
		'''Get file by numeric id (`int` or `long`)
		
		:rtype: `FileResource`
		'''
		
		raise NotImplementedError()
	
	@abc.abstractmethod
	def set_file(self, file_obj, create=True):
		'''Set file
		
		:parameters:
			create : `bool`
				If `False`, don't add the file to the database and return
				`None`
		
		:rtype: `int`
		'''
		
		raise NotImplementedError()

