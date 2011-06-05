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
import glob


from lxml.html.builder import *

import base
from .. import dataobject
from .. import serializer
from .. import resoptimizer
from .. import configloader
from .. import util

class WUI(base.BaseComponent):
	default_config = configloader.DefaultSectionConfig('wui',
		title_suffix='',
		optimize_scripts=True,
		optimize_styles=True,
		scripts_dir='scripts',
		styles_dir='styles',
	)
	
	HTML = 'html'
	
	def setup(self):
		self._content_type = 'text/html'
		self._format = self.HTML
		self._content = None
	
	def render(self):
		if self._content is not None:
			# TODO : other formats, ie rss
			self.context.response.set_content_type('text/html')
			return self._content.renderer.to_html(self.context, self._content)
		
	@property
	def content(self):
		return self._content
	
	@content.setter
	def content(self, o):
		self._content = o
	

class Document(dataobject.ContextAware, dataobject.BaseModel, list):
	class Renderer(dataobject.BaseRenderer):
		@staticmethod
		def to_html(context, model):
			head = HEAD(
				E.meta(charset='utf-8'),
			)
			
			title_list = []
			if model.meta.title:
				title_list.append(model.meta.title)
			
			title_suffix = context.config.wui.title_suffix
			if title_suffix:
				if title_list:
					title_list.append(u' – ')
				title_list.append(title_suffix)
			
			if title_list:
				title = ''.join(title_list)
				head.append(TITLE(title))
			
			Document.Renderer._resource(context, head, filenames=model.styles,
				optimize=context.config.wui.optimize_styles, format='css')
			Document.Renderer._resource(context, head, filenames=model.scripts,
				optimize=context.config.wui.optimize_scripts, format='js')
			
			for name in model.meta:
				meta_element = E.meta(name=name, content=model.meta[name])
				head.append(meta_element)
			
			content_wrapper_element = DIV()
			body_wrapper_element = DIV(content_wrapper_element, id='body-wrapper')
			body_element = BODY(body_wrapper_element)
			html = HTML(head, body_element)
			
			header_content = model.header_content
			footer_content = model.footer_content
			
			if header_content:
				body_wrapper_element.insert(0, header_content.renderer.to_html(context, header_content))
			
			if footer_content:
				body_wrapper_element.append(footer_content.renderer.to_html(context, header_content))
			
			if model.meta.title:
				content_wrapper_element.append(H1(model.meta.title))
			
			if model.meta.subtitle:
				content_wrapper_element.append(H2(model.meta.subtitle))
			
			if model.messages:
				messages_wrapper = E.aside(id='messages')
				content_wrapper_element.append(messages_wrapper)
				
				for title, subtitle, icon in model.messages:
					element = E.section(DIV(title, CLASS='messageTitle'), 
						CLASS='messageBox')
					if subtitle:
						element.append(DIV(subtitle, CLASS='messageSubtitle'))
					
					messages_wrapper.append(element)
			
			for content in model:
				c = content.renderer.to_html(context, content)
				content_wrapper_element.append(c)
			
			return serializer.render_html_element(html, format='html')
		
		@staticmethod
		def _resource(context, head, filenames=None, dirname=None, optimize=True,
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
						context.dirinfo.www, name), filenames)
					s = resoptimizer.optimize(paths, format=format)
				else:
					s = resoptimizer.optimize_dir(dirname, format=format)
				head.append(element_class(s.read()))
			else:
				for p in filenames:
					url = fardel.make_url(paths=(fardel.com.static_file.name, p))
					href = unicode(url)
					head.append(element_class(href=href))
	
	renderer = Renderer
	
	def __init__(self, *args, **kargs):
		super(Document, self).__init__(*args, **kargs)
		self._header_content = None
		self._footer_content = None
		
		self._scripts = []
		self._styles = []
		self._meta = dataobject.DataObject()
		self._messages = []
		
		wui_component = self.context.get_instance(WUI)
		wui_component.content = self
		
		if not '_doc_scriptsstyles' in wui_component.singleton.__dict__:
			styles = []
			scripts = []
			scripts_dir = self.context.config.wui.scripts_dir
			if scripts_dir:
				scripts_dir = os.path.join(self.context.dirinfo.www, scripts_dir)
				
				for p in glob.glob('%s/*.js' % scripts_dir):
					filename = p.replace(self.context.dirinfo.www, '')
					scripts.append(p)
		
			styles_dir = self.context.config.wui.styles_dir
			if styles_dir:
				styles_dir = os.path.join(self.context.dirinfo.www, styles_dir)
				
				for p in glob.glob('%s/*.css' % styles_dir):
					filename = p.replace(self.context.dirinfo.www, '')
					styles.append(p)
			
			wui_component.singleton._doc_scriptsstyles = (scripts, styles)
		
		scripts, styles = wui_component.singleton._doc_scriptsstyles
		self._scripts.extend(scripts)
		self._styles.extend(styles)
		
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
	
#	@property
#	def optimize_scripts(self):
#		return self.optimize_scripts
#	
#	@optimize_scripts.setter
#	def optimize_scripts(self, b):
#		self._optimize_scripts = b
#	
#	@property
#	def optimize_styles(self):
#		return self._optimize_styles
#	
#	@optimize_styles.setter
#	def optimize_styles(self, b):
#		self._optimize_styles = b
	
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
	
	@property
	def header_content(self):
		return self._header_content
	
	@header_content.setter
	def header_content(self, v):
		self._header_content = v

	@property
	def footer_content(self):
		return self._footer_content
	
	@footer_content.setter
	def footer_content(self, v):
		self._footer_content = v
	
	def add_message(self, title, subtitle=None, icon=None):
		self._messages.append((title, subtitle, icon))
	
	@property
	def messages(self):
		return self._messages

class Form(dataobject.BaseModel):
	class Options(list):
		def __init__(self, name, label='', multi=False):
			self.multi = multi
			self.name = name
			self.label = label
		
		def option(self, name, label, active=False):
			self.append((name, label, active))
		
		def to_html(self, context):
			element = DIV(DIV(self.label))
			
			for name, label, active in self:
				element.append(LABEL(label))
				
				if self.multi or len(self) == 1:
					input_type = 'checkbox' 
				else:
					input_type = 'radio'
				
				input = INPUT(type=input_type, name=self.name, value=name)	
				element.append(input)
				
				if context.request.form.getfirst(self.name) == name:
					input.set('checked', 'checked')
			
			return element		
	
	class Group(list):
		def __init__(self, label=None, elements=None):
			if elements:
				super(Group, self).__init__(elements)
			
			self.label = label
			
		def to_html(self, context):
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
		
		def to_html(self, context):
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
		
		def to_html(self, context):
			form_element_id = 'form.%s.%s' 
			element = DIV()
			
			value = context.request.form.getfirst(self.name, '')
			
			if self.validation != 'hidden':
				element.append(LABEL(self.label, FOR=self.name))
			
			if self.validation == 'hidden':
				element.append( INPUT(
					name=self.name,
					type=self.validation,
					value=self.value or self.label) )
			elif self.large:
				element.append(TEXTAREA(self.value or value, name=self.name))
			else:
				input_element = INPUT(
					name=self.name,
					type=self.validation or 'text', 
					value=self.value or value, placeholder=self.label)
				
				if self.required:
					input_element.set('required', 'required')
				
				element.append(input_element)
			
			return element
	
	class Renderer(dataobject.BaseRenderer):
		@staticmethod
		def to_html(context, model):
			form_element = FORM(method=model.method, action=model.url)
			
			for o in model._data:
				form_element.append(o.to_html(context))
			
			return form_element
	
	renderer = Renderer
	
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
	class Renderer(dataobject.BaseRenderer):
		def _render_cell(self, context, cell):
			if isinstance(cell, BaseModel):
				value = cell.renderer.to_html(context, cell)
			else:
				value = cell
			
			return value
		
		def to_html(self, context, model):
			table = TABLE()
			
			if model.get_headers():
				tr = TR()
				table.append(tr)
				
				for v in model.get_headers():
					tr.append(TH(self._render_cell(context, v)))
			
			for row in model.get_rows():
				tr = TR()
				table.append(tr)
				
				for v in row:
					tr.append(TD(self._render_cell(context, v)))
			
			return table
	
	renderer = Renderer
	
	def __init__(self):
		super(Table, self).__init__()
		self._rows = []
		self._headers = []
	
	def set_headers(self, *cols):
		self._headers = cols
	
	def get_headers(self):
		return self._headers
	
	def add_row(self, *cols):
		self._rows.append(tuple(cols))
	
	def get_rows(self):
		return self._rows
	
#class Pager(WUIContent):	
#	def __init__(self, page=0, start=0, end=None, has_more=None,
#	items_per_page=20, url=None):
#		super(Pager, self).__init__()
#		self._page = page
#		self._start = start
#		self._end = end
#		self._has_more = has_more
#		self._items_per_page = items_per_page
#		self._url = url
#	
#	def to_html(self):
#		ul = UL(CLASS='pager')
#		
#		max_page = end / items_per_page
#		self._page = max_page
#		
#		def add(label, page):
#			self._url.query['page'] = page
#			ul.append(LI(A(label, href=str(url))))
#		
#		if self._page:
#			add(u'⇱', 0)
#		
#		if self._page > 1:
#			add(u'⇞', self._page - 1)
#		
#		add(str(self._page), self._page)
#		
#		if self._has_more:
#			add(u'⇟', self._page + 1)
#		
#		if self._end and self._page < max_page:
#			add(u'⇲', max_page)
#		
#		return ul
