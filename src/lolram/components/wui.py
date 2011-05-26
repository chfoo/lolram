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

__doctype__ = 'restructuredtext en'

import os


from lxml.html.builder import *

import base
from .. import dataobject
from .. import serializer
from .. import resoptimizer
from .. import configloader
from .. import util

class WUIAgent(base.BaseComponentAgent):
	def __init__(self, fardel, manager):
		self._manager = manager
		self._fardel = fardel
		self._title_suffix = fardel.conf.wui.title_suffix
		self._scripts = []
		self._styles = []
		self._optimize_scripts = True
		self._optimize_styles = True
		self._scripts_dir = os.path.join(self._fardel.dirs.www, 
			fardel.conf.wui.scripts_dir)
		self._styles_dir = os.path.join(self._fardel.dirs.www,
			fardel.conf.wui.styles_dir)
		self._meta = dataobject.DataObject()
		self._content = []
		self._render_cb_dict = {'html': self.to_html}
	
	def setup(self, fardel):
		fardel.doc = self
	
	def render(self, fardel):
		fardel.resp.set_content_type('text/html')
		return self._render_cb_dict['html']()
		
	@property
	def render_cb_dict(self):
		return self._render_cb_dict
	
	@property
	def content(self):
		return self._content
	
	@content.setter
	def content(self, o):
		self._content = o
	
	@property
	def title(self):
		return self._meta.title
	
	@title.setter
	def title(self, s):
		self._meta.title = s
	
	@property
	def title_suffix(self):
		return self._title_suffix
	
	@title_suffix.setter
	def title_suffix(self, s):
		self._title_suffix = s
	
	@property
	def scripts(self):
		return self._scripts
	
	@property
	def styles(self):
		return self._styles
	
	@property
	def optimize_scripts(self):
		return self.optimize_scripts
	
	@optimize_scripts.setter
	def optimize_scripts(self, b):
		self._optimize_scripts = b
	
	@property
	def optimize_styles(self):
		return self._optimize_styles
	
	@optimize_styles.setter
	def optimize_styles(self, b):
		self._optimize_styles = b
	
	@property
	def scripts_dir(self):
		return self._scripts_dir
	
	@scripts_dir.setter
	def scripts_dir(self, s):
		self._scripts_dir = s
	
	@property
	def styles_dir(self):
		return self._styles_dir
	
	@styles_dir.setter
	def styles_dir(self, s):
		self._styles_dir = s
	
	@property
	def meta(self):
		return self._meta
	
	def to_html(self):
		head = HEAD(
			E.meta(chartset='utf-8'),
		)
		
		title_list = []
		if self._meta.title:
			title_list.append(self._meta.title)
		
		if self._title_suffix:
			if title_list:
				title_list.append(u' – ')
			title_list.append(self._title_suffix)
		
		if title_list:
			title = ''.join(title_list)
			head.append(TITLE(title))
		
		self._resource(self._fardel, head, self._styles, self._styles_dir,
			self._optimize_styles, format='css')
		self._resource(self._fardel, head, self._scripts, self._scripts_dir,
			self._optimize_scripts, format='js')
		
		for name in self._meta:
			meta_element = E.meta(name=name, content=self._meta[name])
			head.append(meta_element)
		
		site_header = E.header(id='site-header')
		site_footer = E.footer(id='site-footer')
		body_wrapper_element = DIV(site_header, site_footer, id='body-wrapper')
		body_element = BODY(body_wrapper_element)
		html = HTML(head, body_element)
		
		header_content = self.get_header_content(self._fardel)
		footer_content = self.get_footer_content(self._fardel)
		
		if header_content:
			site_header.extend(header_content)
		
		if footer_content:
			footer_content = site_footer.extend(footer_content)
		
		if self._content and isinstance(self._content, list):
			body_wrapper_element[1:1] = map(lambda e: e.render(format='html'), 
				self._content)
		elif self._content:
			body_wrapper_element.insert(1, self._content.render(format='html'))
		else:
			body_wrapper_element.insert(1, 
				E.section(PRE(unicode(self._fardel.data))))
		
		return serializer.render_html_element(html, format='html')

	def _resource(self, fardel, head, filenames=None, dirname=None, optimize=True,
	format='js'):
		element_class = None
		
		if format == 'js':
			element_class = E.script
		elif format == 'css':
			element_class = E.style
		else:
			raise Exception('not supported')
		
		if optimize:
			if filenames:
				paths = map(lambda name: os.path.join(
					fardel.dirs.www, name), filenames)
				s = resoptimizer.optimize(paths, format=format)
			else:
				s = resoptimizer.optimize_dir(dirname, format=format)
			head.append(element_class(s.read()))
		else:
			for p in filenames:
				url = fardel.make_url(paths=(fardel.com.static_file.name, p))
				href = unicode(url)
				head.append(element_class(href=href))
	
	def get_header_content(self, fardel):
		# TODO: common website header stuff
		# eg: user actions, login, logout, messages
		# clients should override this function for now
		pass
	
	def get_footer_content(self, fardel):
		# TODO: common website footer stuff
		# eg: copyright
		# clients should override this function for now
		pass

class WUIManager(base.BaseComponentManager):
	name = 'wui'
	agent_class = WUIAgent
	default_config = configloader.DefaultSectionConfig('wui',
		title_suffix='',
		optimize_scripts=True,
		optimize_styles=True,
		scripts_dir='scripts',
		styles_dir='styles',
	)

class WUIContent(object):
	def __init__(self):
		self._cb_dict = {'html':self.to_html}
		
	def render(self, format='html'):
		return self._cb_dict[format]()
	
	def to_html(self):
		raise NotImplementedError()



class Form(WUIContent):
	GET = 'GET'
	POST = 'POST'
	
	class Options(list):
		def __init__(self, name, label='', multi=False):
			self.multi = multi
			self.name = name
			self.label = label
		
		def option(self, name, label, active=False):
			self.append((name, label, active))
		
		def to_html(self):
			element = DIV(DIV(self.label))
			
			for name, label, active in self:
				element.append(LABEL(label))
				
				if self.multi or len(self) == 1:
					input_type = 'checkbox' 
				else:
					input_type = 'radio'
				
				element.append(INPUT(type=input_type, name=self.name,
					value=name))
			
			return element		
	
	class Group(list):
		def __init__(self, label=None, elements=None):
			if elements:
				super(Group, self).__init__(elements)
			
			self.label = label
			
		def to_html(self):
			element = E.fieldset()
			
			if self.label:
				element.append(E.legend(self.label))
			
			for e in self:
				element.append(e.to_html())
			
			return element
			
			
	class Button(object):
		def __init__(self, name, label, icon=None):
			self.name = name
			self.label = label
			self.icon = icon
		
		def to_html(self):
			element = E.button(self.label, name=self.name)
			
			if self.icon:
				element.insert(0, IMG(src=self.icon))
			
			return element
	
	class Textbox(object):
		def __init__(self, name, label, value=None, validation=None,
		large=False, required=False):
			self.name = name
			self.label = label
			self.value = value
			self.validation = validation
			self.large = large
			self.required = required
		
		def to_html(self):
			form_element_id = 'form.%s.%s' 
			element = DIV(
				LABEL(self.label, FOR=self.name)
			)
			
			if self.large:
				element.append(TEXTAREA(self.value or '', name=self.name))
			else:
				input_element = INPUT(self.validation or 'text', 
					value=self.value or '', placeholder=self.label)
				
				if self.required:
					input_element.set('required', 'required')
				
				element.append(input_element)
			
			return element
	
	def __init__(self, method='GET', url='', fardel=None):
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
	
	def to_html(self):
		form_element = FORM(method=self.method, action=self.url)
		
		for o in self._data:
			form_element.append(o.to_html())
		
		return form_element
	
	def _add(self, o):
		if self._group is not None:
			self._group.append(o)
		else:
			self._data.append(o)
