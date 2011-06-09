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

__doctype__ = 'restructuredtext en'

import os

import dataobject
import views
import util

class Form(dataobject.BaseModel):
	class Options(list, dataobject.BaseModel):
		default_view = views.FormView.Options
		
		def __init__(self, name, label='', multi=False):
			self.multi = multi
			self.name = name
			self.label = label
		
		def option(self, name, label, active=False):
			self.append((name, label, active))
		
		
	class Group(list, dataobject.BaseModel):
		default_view = views.FormView.Group
		
		def __init__(self, label=None, elements=None):
			if elements:
				super(Group, self).__init__(elements)
			
			self.label = label
		
			
	class Button(dataobject.BaseModel):
		default_view = views.FormView.Button
		
		def __init__(self, name, label, icon=None):
			self.name = name
			self.label = label
			self.icon = icon
		
	
	class Textbox(dataobject.BaseModel):
		default_view = views.FormView.Textbox
		
		def __init__(self, name, label, value=None, validation=None,
		large=False, required=False):
			self.name = name
			self.label = label
			self.value = value
			self.validation = validation
			self.large = large
			self.required = required
		
		
	default_view = views.FormView
	
	GET = 'GET'
	POST = 'POST'
	TEXT = 'text'
	PASSWORD = 'password'
	HIDDEN = 'hidden'
	
	def __init__(self, method='GET', url=''):
		super(Form, self).__init__()
		self.method = method
		self.url = url
		self._data = []
		self._group = None
		self.id = util.bytes_to_b32low(os.urandom(4))
	
	def group_start(self, *args, **kargs):
		self._group = self.Group(*args, **kargs)
		self._data.append(self._group)
		return self._group
	
	def group_end(self):
		self._group = None
	
	def textbox(self, *args, **kargs):
		textbox = self.Textbox(*args, **kargs)
		self._add(textbox)
		return textbox
	
	def options(self, *args, **kargs):
		options = self.Options(*args, **kargs)
		self._add(options)
		return options
		
	def button(self, *args):
		button = self.Button(*args)
		self._add(button)
		return button
	
	def _add(self, o):
		if self._group is not None:
			self._group.append(o)
		else:
			self._data.append(o)
	

class Table(dataobject.BaseModel):
	default_view = views.TableView
	
	def __init__(self):
		super(Table, self).__init__()
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

	
