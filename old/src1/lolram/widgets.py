# encoding=utf8

'''Widgets'''

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

from lolram import models, util, dataobject, views
from lolram.backports import ordereddict
from lolram.components.session import Session
from lolram.models import BaseModel
from lolram.views import DocumentView

class BaseWidget(object):
	default_renderer = None
	
	def __init__(self):
		self._children = []
		self._renderer = self.default_renderer
		self._id = None
		self._style_classes = []
	
	@property
	def id(self):
		return self._id
	
	@id.setter
	def id(self, s):
		self._id = s
		
	@property
	def style_classes(self):
		return self._style_classes
	
	@property
	def children(self):
		return self._children
	
	@children.setter
	def children(self, l):
		self._children = l
	
	def render(self, context, format):
		return self.default_renderer.render(context, self, format)
	
	@property
	def renderer(self):
		return self._renderer
	
	@renderer.setter
	def renderer(self, view):
		self._renderer = view

class Document(dataobject.ContextAware, BaseModel, BaseWidget, list):
	'''The document model
	
	This class inherits from `list` so additional model and views are be 
	added easily. Append `Widget`s to the document.
	'''
	
	class Resource(object):
		SCRIPT = 'script'
		STYLE = 'style'
		
		def __init__(self, type_, filename, include=True):
			self.type = type_
			self.filename = filename
			self.include = include
	
	default_renderer = DocumentView
	
	def __init__(self, *args, **kargs):
		super(Document, self).__init__(*args, **kargs)
		self._resources = []
		self._meta = dataobject.DataObject()
		self._messages = []
		self.header_content = None
		self.footer_content = None
		
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
	def resources(self):
		return self._resources
	
	@property
	def meta(self):
		'''The `dict` of document metadata
		
		:rtype: `dict`
		'''
		return self._meta
	
	def add_message(self, title, subtitle=None, icon=None):
		'''Add a dialogue message to be displayed to the user'''
		
		self._messages.append((title, subtitle, icon))
	
	@property
	def messages(self):
		return self._messages



class HorizontalBox(BaseWidget):
	default_renderer = views.HorizontalBoxView


class VerticalBox(BaseWidget):
	default_renderer = views.VerticalBoxView


class Text(BaseWidget):
	default_renderer = views.TextView
	
	def __init__(self, text=None):
		super(Text, self).__init__()
		self._text = text
	
	@property
	def text(self):
		return self._text
	
	@text.setter
	def text(self, s):
		self._text = s


class Image(models.ImageModel, BaseWidget):
	default_renderer = views.ImageView
	

class Link(models.LinkModel, BaseWidget):
	default_renderer = views.LinkView

class Button(models.ButtonModel, BaseWidget, ):
	default_renderer = views.ButtonView


class Option(models.OptionModel, BaseWidget):
	pass


class OptionGroup(models.OptionGroupModel,BaseWidget, ordereddict.OrderedDict):
	default_renderer = views.OptionGroupView
	
	def __init__(self, *args, **kargs):
		models.OptionGroupModel.__init__(self,*args, **kargs)
		ordereddict.OrderedDict.__init__(self)


class TextBox(models.TextBoxModel, BaseWidget):
	default_renderer = views.TextBoxView


class Form(BaseWidget, models.FormModel, ordereddict.OrderedDict):
	default_renderer = views.FormView
	FORM_SESSION_KEY = '_forms'

	def __init__(self, method=models.FormModel.GET, url=''):
		ordereddict.OrderedDict.__init__(self)
		models.FormModel.__init__(self, method=method, url=url)
		self._id = util.bytes_to_b32low(os.urandom(4))
	
	def validate(self, context):
		sess = Session(context)
		
		if self.FORM_SESSION_KEY not in sess.data:
			sess.data[self.FORM_SESSION_KEY] = self._id
			
		self._id = sess.data[self.FORM_SESSION_KEY]
		self[self.FORM_ID] = TextBox(value=self._id, validation=TextBox.HIDDEN)
		
		
		given_id = context.request.form.getfirst(self.FORM_ID)
		
		if self.FORM_SESSION_KEY not in sess.data:
			return False
		
		id_ = sess.data[self.FORM_SESSION_KEY]
		
		return context.request.is_post and given_id == id_
	
	def populate_values(self, context=None):
		for name, widget in self.iteritems():
			
			if isinstance(widget, TextBox):
				if context:
					form_value = context.request.form.getfirst(name, widget.value or widget.default)
					widget.value = form_value
				
				widget.name = name
			elif isinstance(widget, Option):
				if context:
					form_value = context.request.form.getfirst(name, widget.active or widget.default)
					widget.active = form_value is not None
				
				widget.name = name
				
			elif isinstance(widget, OptionGroup):
				widget.name = name
				
				if context and name in context.request.form:
					form_values = context.request.form.getlist(name)
				
					for subname, subwidget in widget.iteritems():
						subwidget.active = subname in form_values
				
				for subname, subwidget in widget.iteritems():
					subwidget.name = subname
				
			elif isinstance(widget, Button):
				widget.name = name
			else:
				raise Exception('unknown widget')
	
	def render(self, *args, **kargs):
		self.populate_values()
		return super(Form, self).render(*args, **kargs)


class NavigationBox(HorizontalBox):
	default_renderer = views.NavigationBoxView


class Table(BaseWidget,  models.TableModel):
	default_renderer = views.TableView
	
	def __init__(self, *args, **kargs):
		models.TableModel.__init__(self, *args, **kargs)
		self.row_views = kargs.get('row_views')
		self.header_views = kargs.get('header_views')
		self.footer_views = kargs.get('footer_views')
		

class Pager(BaseWidget, dataobject.PageInfo):
	default_renderer = views.PagerView
	
	def __init__(self, page_info=None, context=None, **kargs):
		dataobject.PageInfo.__init__(self, **kargs)
		if page_info:
			self.limit = page_info.limit
			self.page = page_info.page
			self.offset = page_info.offset
			self.more = page_info.more
		
		if context:
			self.populate(context)
	
	def populate(self, context):
		self.page = max(1, int(context.request.query.getfirst('page', 0)))
		self.offset = (self.page - 1) * self.limit
		
		if self.all is not None:
			self.page_max = self.all // self.limit + 1

