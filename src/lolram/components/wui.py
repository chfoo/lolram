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
			return self._content.render(self.context, 'html')
		
	@property
	def content(self):
		'''The `MVPair`'''
		return self._content
	
	@content.setter
	def content(self, o):
		self._content = o


class DocumentView(dataobject.BaseView):
	@classmethod
	def to_html(cls, context, model, **opts):
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
		
		cls._resource(context, head, filenames=model.styles,
			optimize=context.config.wui.optimize_styles, format='css')
		cls._resource(context, head, filenames=model.scripts,
			optimize=context.config.wui.optimize_scripts, format='js')
		
		for name in model.meta:
			meta_element = E.meta(name=name, content=model.meta[name] or '')
			head.append(meta_element)
		
		content_wrapper_element = DIV()
		body_wrapper_element = DIV(content_wrapper_element, id='body-wrapper')
		body_element = BODY(body_wrapper_element)
		html = HTML(head, body_element)
		
		header_content = model.header_content
		footer_content = model.footer_content
		
		if header_content:
			body_wrapper_element.insert(0, header_content.render(context, 'html'))
		
		if footer_content:
			body_wrapper_element.append(footer_content.render(context, 'html'))
		
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
			assert isinstance(content, dataobject._MVPair)
			c = content.render(context, 'html', **opts)
			content_wrapper_element.append(c)
		
		return serializer.render_html_element(html, format='html')
	
	@classmethod
	def _resource(cls, context, head, filenames=None, dirname=None, optimize=True,
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


class Document(dataobject.ContextAware, dataobject.BaseModel, list):
	'''The document model
	
	This class inherits from `list` so additional model and views are be 
	added easily. Append `MVPair`s to the document.
	'''
	
	default_view = DocumentView
	
	def __init__(self, *args, **kargs):
		super(Document, self).__init__(*args, **kargs)
		self._header_content = None
		self._footer_content = None
		
		self._scripts = []
		self._styles = []
		self._meta = dataobject.DataObject()
		self._messages = []
		
		wui_component = self.context.get_instance(WUI)
		wui_component.content = dataobject.MVPair(self)
		
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
		'''The main title of the document'''
		
		return self._meta.title
	
	@title.setter
	def title(self, s):
		self._meta.title = s
	
	@property
	def title_suffix(self):
		'''An optional suffix appended to the title'''
		
		return self._title_suffix
	
	@title_suffix.setter
	def title_suffix(self, s):
		self._title_suffix = s
	
	@property
	def scripts(self):
		'''Additional paths to JavaScript files to be added to HTML format'''
		
		return self._scripts
	
	@property
	def styles(self):
		'''Additional paths to CSS files to be added to HTML format'''
		
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
		'''The directory in which Javascript files are served'''
		
		return self._scripts_dir
	
	@scripts_dir.setter
	def scripts_dir(self, s):
		self._scripts_dir = s
	
	@property
	def styles_dir(self):
		'''The directory in which CSS files are served'''
		
		return self._styles_dir
	
	@styles_dir.setter
	def styles_dir(self, s):
		self._styles_dir = s
	
	@property
	def meta(self):
		'''The `dict` of document metadata
		
		:rtype: `dict`
		'''
		return self._meta
	
	@property
	def header_content(self):
		'''Default `MVPair` to be used as a header to the document'''
		
		return self._header_content
	
	@header_content.setter
	def header_content(self, v):
		self._header_content = v

	@property
	def footer_content(self):
		'''Default `MVPair` to be used as a footer to the document'''
		
		return self._footer_content
	
	@footer_content.setter
	def footer_content(self, v):
		self._footer_content = v
	
	def add_message(self, title, subtitle=None, icon=None):
		'''Add a dialogue message to be displayed to the user'''
		
		self._messages.append((title, subtitle, icon))
	
	@property
	def messages(self):
		return self._messages



