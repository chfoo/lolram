# encoding=utf8

'''reStructuredText publisher'''

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

import re
import cStringIO as StringIO

import docutils.parsers.rst
import docutils.utils
import docutils.parsers.rst.directives
import docutils.core
import docutils.io

import dataobject

FIELD_RE = re.compile(r':(\w*):((?:[^\\][^:])*)')
PLACEHOLDER_RE = re.compile(r'{{(\w+)}}')

class TemplateDirective(docutils.parsers.rst.Directive):
	required_arguments = 1
	optional_arguments = 1
	option_spec = {}
	has_content = False
	final_argument_whitespace = True
	
	def run(self):
		template_name = self.arguments[0]
		
		fn_result = template_callback(template_name)
		
		if fn_result is None:
			raise self.error(u'Template ‘%s’ not found' % template_name)
		
		else:
			subs_dict = {}
		
			for key, value in re.findall(FIELD_RE, self.arguments[1]):
				subs_dict[key] = value
		
			def f(match):
				key = match.groups()[0]
			
				if key in subs_dict:
					return subs_dict[key]
		
			text = re.sub(PLACEHOLDER_RE, f, fn_result)
		
			self.state_machine.insert_input([text], template_name)
		
		return []

class MathDirective(docutils.parsers.rst.Directive):
	required_arguments = 0
	optional_arguments = 0
	option_spec = {}
	has_content = True
#	final_argument_whitespace = False
	
	def run(self):
		l = []
		for s in self.content:
			l.append(docutils.nodes.Text(s))
		
		return l

class Publisher(object):
	def publish(self, text):
		error_stream = StringIO.StringIO()
		settings = {
			'halt_level' : 5,
			'warning_stream' : error_stream,
			'file_insertion_enabled' : False,
			'raw_enabled' : False,
		}
		
		output, publisher = docutils.core.publish_programmatically(
			source_class=docutils.io.StringInput, source=text, 
			source_path=None, 
			destination_class=docutils.io.NullOutput, destination=None, 
			destination_path=docutils.io.NullOutput.default_destination_path, 
			reader=None, reader_name='standalone', 
			parser=None, parser_name='restructuredtext', 
			writer=None, writer_name='html', 
			settings=None, settings_spec=None, settings_overrides=settings, 
			config_section=None, enable_exit_status=None) 
		
		doc_info = {}
		document = publisher.writer.document
		doc_info['tree'] = self.format_tree(document)
		error_stream.seek(0)
		doc_info['errors'] = error_stream.read()
		doc_info['title'] = document.get('title')
		doc_info['subtitle'] = document.get('subtitle')
		doc_info['meta'] = {}
		i = publisher.document.first_child_matching_class(docutils.nodes.docinfo)
		if i is not None:
			docinfo = document[i]
		
			for node in docinfo:
				doc_info['meta'][node.tagname] = node.astext()
		
		doc_info['refs'] = {}
		for name, node_list in document.refnames.iteritems():
			doc_info['refs'][name] = map(self.format_tree, node_list)
		
		doc_info['html-parts'] = publisher.writer.parts
		
		return doc_info
	
	def format_tree(self, document):
		if isinstance(document, docutils.nodes.Text):
			return document.astext()
		elif isinstance(document, docutils.nodes.reference):
			return {
				'tag' : document.tagname,
				'values' : [document.attributes['refuri']]
			}
		else:
			d = {}
			tag = document.tagname
			d['tag'] = tag
			d['values'] = []
			for child in document.children:
				value = self.format_tree(child)
				d['values'].append(value)
			return d
	

docutils.parsers.rst.directives.register_directive('template', TemplateDirective)
docutils.parsers.rst.directives.register_directive('math', MathDirective)

def template_callback(name):
	raise NotImplementedError()

def publish_text(text):
	p = Publisher()
	return p.publish(text)
