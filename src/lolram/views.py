# encoding=utf8

'''View Renderers'''

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

import lxml.html.builder as lxmlbuilder

from lolram import serializer, resoptimizer

class BaseView(object):
	'''Base class for views
	
	Subclasses should define static methods with the name ``to_FORMAT``
	and have the method signature ``(context, model, **opts)``
	
	'''
	
	__slots__ = ()
	
	@classmethod
	def supports(cls, format):
		return 'to_%s' in dir(cls)
	
	@classmethod
	def render(cls, context, model, format, **opts):
		return getattr(cls, 'to_%s' % format)(context, model, **opts)


class DocumentView(BaseView):
	@classmethod
	def to_html(cls, context, model, **opts):
		head = lxmlbuilder.HEAD(
			lxmlbuilder.E.meta(charset='utf-8'),
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
			head.append(lxmlbuilder.TITLE(title))
		
		styles = []
		scripts = []
		for resource in model.resources:
			if resource.type == 'style':
				styles.append(resource.filename)
			else:
				scripts.append(resource.filename)
		
		cls._resource(context, head, filenames=styles,
			optimize=context.config.wui.optimize_styles, format='css')
		cls._resource(context, head, filenames=scripts,
			optimize=context.config.wui.optimize_scripts, format='js')
		
		for name in model.meta:
			meta_element = lxmlbuilder.E.meta(name=name, content=model.meta[name] or '')
			head.append(meta_element)
		
		content_wrapper_element = lxmlbuilder.DIV()
		body_wrapper_element = lxmlbuilder.DIV(content_wrapper_element, id='body-wrapper')
		body_element = lxmlbuilder.BODY(body_wrapper_element)
		html = lxmlbuilder.HTML(head, body_element)
		
		header_content = model.header_content
		footer_content = model.footer_content
		
		if header_content:
			body_wrapper_element.insert(0, header_content.render(context, 'html'))
		
		if footer_content:
			body_wrapper_element.append(footer_content.render(context, 'html'))
		
		if model.meta.title:
			content_wrapper_element.append(lxmlbuilder.H1(model.meta.title))
		
		if model.meta.subtitle:
			content_wrapper_element.append(lxmlbuilder.H2(model.meta.subtitle))
		
		if model.messages:
			messages_wrapper = lxmlbuilder.E.aside(id='messages')
			content_wrapper_element.append(messages_wrapper)
			
			for title, subtitle, icon in model.messages:
				element = lxmlbuilder.E.section(lxmlbuilder.DIV(title, CLASS='messageTitle'), 
					CLASS='messageBox')
				if subtitle:
					element.append(lxmlbuilder.DIV(subtitle, CLASS='messageSubtitle'))
				
				messages_wrapper.append(element)
		
		for content in model:
#			assert isinstance(content, dataobject.MVPair)
			c = content.render(context, 'html', **opts)
			content_wrapper_element.append(c)
		
		return serializer.render_html_element(html, format='html')
	
	@classmethod
	def _resource(cls, context, head, filenames=None, dirname=None, optimize=True,
	format='js'):
		element_class = None
		
		if format == 'js':
			element_class = lxmlbuilder.E.script
		elif format == 'css':
			element_class = lxmlbuilder.E.style
		else:
			raise Exception('not supported')
		
		if optimize:
			if filenames:
				paths = map(lambda name: os.path.join(
					context.dirinfo.www, name.lstrip('/')), filenames)
				s = resoptimizer.optimize(paths, format=format)
			else:
				s = resoptimizer.optimize_dir(dirname, format=format)
			head.append(element_class(s.read().decode('utf8')))
		else:
			for p in filenames:
				url = context.str(
					path='%s/%' % (context.config.static_file.path_name, p))
				href = unicode(url)
				head.append(element_class(href=href))


class HorizontalBoxView(BaseView):
	@classmethod
	def to_html(cls, context, model):
		element = lxmlbuilder.DIV(lxmlbuilder.CLASS('horizontalBoxView'))
		
		for widget in model.children:
			result = widget.render(context, 'html')
			
			if result is not None:
				e1 = lxmlbuilder.SPAN(result, lxmlbuilder.CLASS('horizontalBoxViewCell'))
				e1.tail = u' '
				element.append(e1)
		
		return element


class VerticalBoxView(BaseView):
	@classmethod
	def to_html(cls, context, model):
		element = lxmlbuilder.DIV(lxmlbuilder.CLASS('verticalBoxView'))
		
		for widget in model.children:
			result = widget.render(context, 'html')
			
			if result is not None:
				e1 = lxmlbuilder.DIV(result, lxmlbuilder.CLASS('verticalBoxViewCell'))
				element.append(e1)
		
		return element


class NavigationBoxView(BaseView):
	@classmethod
	def to_html(cls, context, model):
		element = lxmlbuilder.E.nav(lxmlbuilder.CLASS('navigationBoxView'))
		
		for widget in model.children:
			result = widget.render(context, 'html')
			
			if result is not None:
				e1 = lxmlbuilder.SPAN(result, lxmlbuilder.CLASS('navigationBoxViewCell'))
				e1.tail = u' '
				element.append(e1)
		
		return element

class TextView(BaseView):
	@classmethod
	def to_html(cls, context, model):
		return lxmlbuilder.SPAN(model.text, lxmlbuilder.CLASS('textView'))


class ImageView(BaseView):
	@classmethod
	def to_html(cls, context, model):
		return lxmlbuilder.IMG(lxmlbuilder.CLASS('imageView'),
			src=model.url, alt=model.alt)


class LinkView(BaseView):
	@classmethod
	def to_html(cls, context, model):
		element = lxmlbuilder.A(lxmlbuilder.CLASS('linkView'))
		
		if model.image:
			element.append(model.image.render(context, 'html'))
		
		if model.label:
			element.text = model.label
		
		if model.url:
			element.set('href', model.url)
		
		return element


class ButtonView(BaseView):
	@classmethod
	def to_html(cls, context, model):
		element = lxmlbuilder.E.button(model.label, 
			lxmlbuilder.CLASS('buttonView'), name=model.name)
		element.set('type', 'submit')
		
		if model.image:
			element.insert(0, model.image.render(context, 'html'))
		
		return element


class OptionGroupView(BaseView):
	@classmethod
	def to_html(cls, context, model):
		element = lxmlbuilder.DIV(lxmlbuilder.CLASS('optionListView'))
		
		num_options = len(model)
		
		dropdown_element = None
		menu_element = lxmlbuilder.E.menu()
		
		if model.multi or num_options == 1:
			input_type = 'checkbox'
			element.append(menu_element)
		elif num_options <= 3:
			input_type = 'radio'
			element.append(menu_element)
		else:
			input_type = 'dropdown'
			element.append(lxmlbuilder.LABEL(model.label, 
				lxmlbuilder.FOR(model.name)))
			dropdown_element = lxmlbuilder.SELECT(name=model.name, id=model.name)
			element.append(dropdown_element)
		
		for option in model.itervalues():
			label = option.label
			name = option.name
			active = option.active or option.default
			
			if dropdown_element:
				opt_e = lxmlbuilder.OPTION(label, value=label)
				
				if active:
					opt_e.set('selected', 'selected')
					
				dropdown_element.append(opt_e)
				
			else:
				div = lxmlbuilder.DIV()
				div.append(lxmlbuilder.LABEL(label, lxmlbuilder.FOR(model.name+name)))
				input = lxmlbuilder.INPUT(type=input_type, id=model.name+name, 
					name=model.name, value=name)	
				div.append(input)
			
				if active:
					input.set('checked', 'checked')
			
				element.append(div)
		
		return element		


class TextBoxView(BaseView):
	@classmethod
	def to_html(cls, context, model):
		form_element_id = 'form.%s' % (model.name)
		element = lxmlbuilder.DIV()
		
		value = model.value or model.default or u''
	
		if model.validation != 'hidden':
			element.append(lxmlbuilder.LABEL(model.label, 
				lxmlbuilder.FOR(form_element_id)))
		
		if model.validation == 'hidden':
			element = lxmlbuilder.INPUT(
				name=model.name,
				type=model.validation,
				value=value)
		elif model.large:
			element.append(lxmlbuilder.TEXTAREA(
				value, 
				id=form_element_id,
				name=model.name))
		else:
			input_element = lxmlbuilder.INPUT(
				id=form_element_id,
				name=model.name,
				type=model.validation or 'text', 
				placeholder=model.label)
			
			if value:
				input_element.set('value', value)
			
			if model.required:
				input_element.set('required', 'required')
			
			element.append(input_element)
		
		return element



class FormView(BaseView):
	@classmethod
	def to_html(cls, context, model):
		model.populate_values()
		form_element = lxmlbuilder.FORM(method=model.method, action=model.url)
		
		if model.method == 'POST':
			form_element.set('enctype', "multipart/form-data")
		
		for key, widget in model.iteritems():
			form_element.append(widget.render(context, 'html'))
		
		return form_element


class TableView(BaseView):
	@classmethod
	def to_html(cls, context, model, row_views=None, header_views=None, footer_views=None):
		header_views = model.header_views or header_views
		row_views = model.row_views or row_views
		footer_views = model.footer_views or footer_views
		
		def render_row(row, row_type='row', header_views=header_views, 
		footer_views=footer_views, row_views=row_views):
			if row_type == 'header':
				cell_htmlclass = lxmlbuilder.TH
				row_views = header_views
			elif row_type == 'footer':
				cell_htmlclass = lxmlbuilder.TH
				row_views = footer_views
			else:
				cell_htmlclass = lxmlbuilder.TD
			
			row_element = lxmlbuilder.TR()
			
			for i in xrange(len(row)):
				data = row[i]
				
				if row_views and row_views[i]:
					data = row_views[i].render(context, data, 'html')
				
				row_element.append(cell_htmlclass(data))
			
			return row_element
		
		table = lxmlbuilder.TABLE()
		
		if model.header:
			table.append(render_row(model.header, row_type='header'))
		
		if model.rows:
			table.extend([render_row(row, row_type='row') for row in model.rows])
		
		if model.footer:
			table.append(render_row(model.footer, row_type='footer'))
		
		return table


class ToUnicodeView(BaseView):
	@classmethod
	def supports(cls, format):
		return True
	
	@classmethod
	def render(cls, context, model, format='html'):
		return unicode(model)


class ToURLView(BaseView):
	@classmethod
	def to_html(cls, context, model):
		return lxmlbuilder.A(model, href=model)

class LabelURLToLinkView(BaseView):
	@classmethod
	def to_html(cls, context, model):
		return lxmlbuilder.A(model[0], href=model[1])

class PagerView(BaseView):
	@classmethod
	def to_html(cls, context, model, **opts):
		ul = lxmlbuilder.E.nav(CLASS='pager')
		
		def add(label, page):
			url = context.str_url(fill_path=True, fill_query=True, 
				fill_params=True, query={'page':str(page)})
			e = lxmlbuilder.A(label, href=url)
			e.tail = u' '
			ul.append(e)
		
		if model.page_min and model.page > 1:
			add(u'⇱', 1)
		
		if model.page > 2:
			add(u'⇞', model.page - 1)
		
#		lio = context.get_instance(components.lion.Lion)
		
#		add(lio.formatter.number(model.page), model.page)
		
		if model.more:
			add(u'⇟', model.page + 1)
		
		if model.page_max and model.page < model.page_max:
			add(u'⇲', model.page_max)
		
		return ul

class NavView(BaseView):
	@classmethod
	def to_html(cls, context, model):
		ul = lxmlbuilder.E.nav(lxmlbuilder.CLASS('navView'))
		
		for label, url, icon in model._data:
			a = lxmlbuilder.A(label, href=url)
			a.tail = u' '
			if icon:
				a.insert(0, lxmlbuilder.IMG(src=icon))
			
			ul.append(a)
		
		return ul