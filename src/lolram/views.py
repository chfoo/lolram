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

import dataobject
import lxml.html.builder as lxmlbuilder

class FormView(dataobject.BaseView):
	class Options(dataobject.BaseView):
		@classmethod
		def to_html(cls, context, model, **opts):
			element = lxmlbuilder.DIV(lxmlbuilder.DIV(model.label))
			
			for name, label, active, default in model:
				div = lxmlbuilder.E.menu()
				div.append(lxmlbuilder.LABEL(label, lxmlbuilder.FOR(model.name+name)))
				
				if model.multi or len(model) == 1:
					input_type = 'checkbox' 
				else:
					input_type = 'radio'
				
				input = lxmlbuilder.INPUT(type=input_type, id=model.name+name, 
					name=model.name, value=name)	
				div.append(input)
				
				values = context.request.form.getlist(model.name)
				if name in values or (name not in values and default) or active:
					input.set('checked', 'checked')
				
				element.append(div)
			
			return element		
	
	
	class Group(dataobject.BaseView):
		@classmethod
		def to_html(cls, context, model, **opts):
			element = lxmlbuilder.E.fieldset()
			
			if model.label:
				element.append(lxmlbuilder.E.legend(model.label))
			
			for e in model:
				element.append(dataobject.MVPair(e).render(context, 'html'))
			
			return element
	
	class Button(dataobject.BaseView):
		@classmethod
		def to_html(cls, context, model, **opts):
			element = lxmlbuilder.E.button(model.label, name=model.name)
			element.set('type', 'submit')
			
			if model.icon:
				element.insert(0, lxmlbuilder.IMG(src=model.icon))
			
			return element
	
	class Textbox(dataobject.BaseView):
		@classmethod
		def to_html(cls, context, model, **opts):
			form_element_id = 'form.%s.%s' % (opts['form_model'].id, model.name)
			element = lxmlbuilder.DIV()
			
			value = context.request.form.getfirst(model.name)
			
			if model.validation != 'hidden':
				element.append(lxmlbuilder.LABEL(model.label, 
					lxmlbuilder.FOR(form_element_id)))
			
			if model.validation == 'hidden':
				element = lxmlbuilder.INPUT(
					name=model.name,
					type=model.validation,
					value=model.value or model.default or model.label)
			elif model.large:
				element.append(lxmlbuilder.TEXTAREA(
					model.value or value or model.default or '', 
					id=form_element_id,
					name=model.name))
			else:
				input_element = lxmlbuilder.INPUT(
					id=form_element_id,
					name=model.name,
					type=model.validation or 'text', 
					placeholder=model.label)
				
				if model.value or value or model.default:
					input_element.set('value', model.value or value or model.default)
				
				if model.required:
					input_element.set('required', 'required')
				
				element.append(input_element)
			
			return element
	
	
	@classmethod
	def to_html(cls, context, model):
		form_element = lxmlbuilder.FORM(method=model.method, action=model.url)
		
		if model.method == 'POST':
			form_element.set('enctype', "multipart/form-data")
		
		for o in model._data:
			form_element.append(dataobject.MVPair(o).render(
				context, 'html', form_model=model))
		
		return form_element


class TableView(dataobject.BaseView):
	@classmethod
	def to_html(cls, context, model, header_views=None, footer_views=None, 
	row_views=None, **opts):
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
					data = row_views[i].render(context, data, 'html', **opts)
				
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


class ToUnicodeView(dataobject.BaseView):
	@classmethod
	def supports(cls, format):
		return True
	
	@classmethod
	def render(cls, context, model, format='html'):
		return unicode(model)


class ToURLView(dataobject.BaseView):
	@classmethod
	def to_html(cls, context, model):
		return lxmlbuilder.A(model, href=model)

class LabelURLToLinkView(dataobject.BaseView):
	@classmethod
	def to_html(cls, context, model):
		return lxmlbuilder.A(model[0], href=model[1])

class PagerView(dataobject.BaseView):
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
		
		add(str(model.page), model.page)
		
		if model.more:
			add(u'⇟', model.page + 1)
		
		if model.page_max and model.page < model.page_max:
			add(u'⇲', model.page_max)
		
		return ul

class NavView(dataobject.BaseView):
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