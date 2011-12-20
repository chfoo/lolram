#encoding=utf8

'''Form builder and validation'''

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

import os

import lxml.html.builder

import tornado.web


class FormHandlerMixIn(object):
	def validate_form(self):
		return self.session.key == self.get_argument('_form_key')

class Form(dict):
	INPUT_COLOR = 'color'
	INPUT_DATE = 'date'
	INPUT_DATE_TIME = 'datetime'
	INPUT_DATE_TIME_LOCAL = 'datetime-local'
	INPUT_EMAIL = 'email'
	INPUT_FILE = 'file'
	INPUT_MONTH = 'month'
	INPUT_NUMBER = 'number'
	INPUT_PASSWORD = 'password'
	INPUT_RANGE = 'range'
	INPUT_SEARCH = 'search'
	INPUT_TEL = 'tel'
	INPUT_TEXT = 'text'
	INPUT_TIME = 'time'
	INPUT_URL = 'url'
	INPUT_WEEK = 'week'
	
	class Options(list):
		def add(self, name, label, active=False):
			self.append((name, label, active))
	
	def __init__(self, method='POST', url=''):
		self['method'] = method
		self['url'] = url
		self['key'] = None
		self['elements'] = []
	
	def add_button(self, name, label):
		self['elements'].append(('button', name, label))
	
	def add_input(self, name, label, type_=INPUT_TEXT, value=None, required=False):
		self['elements'].append(('input', name, label, type_, required, value))
	
	def add_options(self, name, label, multi=False):
		options = self.Options()
		self['elements'].append(('options', name, label, options, multi))
		return options


class FormUIModule(tornado.web.UIModule):
	model = Form
	
	def render(self, form_data):
		form_id = os.urandom(2).encode('hex')
		b = lxml.html.builder
		
		form_element = b.FORM(
			b.INPUT(name='_key_name', value=form_data['key'] or self.handler.session.key),
			method=form_data['method'],
			action=form_data['url']
		)
		
		for element in form_data['elements']:
			element_type = element[0]
			field_id = '%s:%s' % (form_id, os.urandom(2).encode('hex'))
			
			if element_type == 'button':
				button_element = b.INPUT(
					type='submit',
					name=element[1],
					value=element[2],
				)
				form_element.append(button_element)
			elif element_type == 'input':
				
				label_element = b.LABEL(
					element[2],
					b.FOR(field_id)
				)
				input_element = b.INPUT(
					name=element[1],
					type=element[3],
					id=field_id,
					placeholder=element[2],
				)
				
				if element[4]:
					input_element.set('required', 'required')
				
				if element[5] is not None:
					input_element.set('value', element[5])
					
				form_element.append(label_element)
				form_element.append(input_element)
			elif element_type == 'options':
				label_element = b.LABEL(
					element[2],
					b.FOR(field_id)
				)
				
				multi = element[4] or len(element[3]) == 1
				
				if multi:
					options_element = b.DIV(id=field_id)
				else:
					options_element = b.SELECT(id=field_id, name=[1])
				
				for name, label, active in element[3]:
					if multi:
						field_block_element = b.DIV()
						subfield_id = '%s:%s' % (field_id, os.urandom(2).encode('hex'))
						input_element = b.INPUT(
							type='checkbox',
							name=element[1],
							value=name,
							id=subfield_id,
						)
						
						if active:
							input_element.set('checked', 'checked')
						
						sublabel_element = b.LABEL(
							label,
							b.FOR(subfield_id),
						)
						
						field_block_element.append(input_element)
						field_block_element.append(sublabel_element)
						options_element.append(field_block_element)
					else:
						option_element = b.OPTION(
							label,
							value=name
						)
						
						if active:
							option_element.set('selected', 'selected')
							
						options_element.append(option_element)
		
		return lxml.html.tostring(form_element, pretty_print=True)