# encoding=utf8

'''Models'''

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

class BaseModel(object):
	'''Base class for models'''
	
	pass


class ButtonModel(BaseModel):
	def __init__(self, name=None, label=None, image=None):
		self.label = label
		self.name = name
		self.image = image


class TextBoxModel(BaseModel):
	TEXT = 'text'
	PASSWORD = 'password'
	HIDDEN = 'hidden'
	FILE = 'file'
	
	def __init__(self, name=None, label=None, value=None, large=False, 
	validation=None, required=False, default=None):
		self.label = label
		self.name = name
		self.value = value
		self.large = large
		self.validation = validation
		self.required = required
		self.default = default


class ImageModel(BaseModel):
	def __init__(self, url=None, alt=None, icon=None):
		self.url = url
		self.alt = alt
		self.icon = icon


class OptionModel(BaseModel):
	def __init__(self,  name=None, label=None, active=False, default=None):
		self.label = label
		self.name = name
		self.active = active
		self.default = default


class OptionGroupModel(BaseModel):
	def __init__(self, multi=False, name=None, label=u''):
		self.multi = multi
		self.name = name
		self.label = label


class LinkModel(BaseModel):
	def __init__(self, label=None, url=None, image=None):
		self.label = label
		self.url = url
		self.image = image


class FormModel(BaseModel):
	GET = 'GET'
	POST = 'POST'
	FORM_ID = 'lrfid'
	
	def __init__(self, method='GET', url=''):
		self._method = method
		self._url = url
	
	@property
	def method(self):
		return self._method
	
	@property
	def url(self):
		return self._url

class TableModel(BaseModel):
	def __init__(self):
		self._rows = []
		self._header = []
		self._footer = []
	
	@property
	def header(self):
		return self._header
	
	@header.setter
	def header(self, o):
		self._header = o
	
	@property
	def footer(self):
		return self._footer
	
	@footer.setter
	def footer(self, o):
		self._footer = o
	
	@property
	def rows(self):
		return self._rows
	
	@rows.setter
	def rows(self, o):
		self.rows = o

