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

__docformat__ = 'restructuredtext en'

import collections
import re
import cStringIO as StringIO
import subprocess
import cgi
import os
import hashlib

import docutils.parsers.rst
import docutils.utils
import docutils.parsers.rst.directives
import docutils.core
import docutils.io
import docutils.parsers.rst.directives.images

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
		
		fn_result = self.state.document.settings \
			.restpub_callbacks['template'](template_name)
		
		if fn_result is None:
			# FIXME: error messages in unicode not supported
			raise self.error('Template %s not found' % template_name)
		
		else:
			subs_dict = {}
			
			if len(self.arguments) >= 2:
				for key, value in re.findall(FIELD_RE, self.arguments[1]):
					subs_dict[key] = value
			
				def f(match):
					key = match.groups()[0]
				
					if key in subs_dict:
						return subs_dict[key]
			
				text = re.sub(PLACEHOLDER_RE, f, fn_result)
			else:
				text = fn_result
		
			self.state_machine.insert_input([text], template_name)
		
		return []

class MathDirective(docutils.parsers.rst.Directive):
	required_arguments = 0
	optional_arguments = 0
	option_spec = {}
	has_content = True
#	final_argument_whitespace = False

	def run(self):
		text = '\n'.join(self.content)
		
		hex_hash = hashlib.md5(text).hexdigest()
		
		src = self.state.document.settings.restpub_callbacks['pre-math'] \
			(hex_hash)
		
		if not src:
			p = subprocess.Popen(['texvc', '/tmp/', '/tmp/', 
				text, 'utf8'], stdout=subprocess.PIPE)
			out, err = p.communicate()
			
			texvc_info = texvc_lexor(out)
			
			l = []
		
			if texvc_info.has_error:
				l.append(docutils.nodes.literal_block(text))
			elif texvc_info.html:
				l.append(docutils.nodes.raw('', texvc_info.html, format='html'))
			else:
				image_path = os.path.join('/tmp/', '%s.png' % texvc_info.hash)
				src = self.state.document.settings \
					.restpub_callbacks['math'](texvc_info.hash, image_path)
		
		if src:
			l.append(docutils.nodes.image(src, alt=text, uri=src, classes=['math']))
			
		return l


class ImageDirective(docutils.parsers.rst.directives.images.Image):
	def run(self):
		self.arguments[0] = self.state.document.settings \
			.restpub_callbacks['image'](self.arguments[0])
		return docutils.parsers.rst.directives.images.Image.run(self)


class FigureDirective(docutils.parsers.rst.directives.images.Figure):
	def run(self):
		self.arguments[0] = self.state.document.settings \
			.restpub_callbacks['image'](self.arguments[0])
		return docutils.parsers.rst.directives.images.Figure.run(self)


class InternalDirective(docutils.parsers.rst.Directive):
	required_arguments = 1
	optional_arguments = 9
	option_spec = {}
	has_content = False
#	final_argument_whitespace = False

	def run(self):
		additional_settings = self.state.document.settings.restpub_additional_settings
		content = self.state.document.settings \
			.restpub_callbacks['internal'](*self.arguments, **additional_settings)
		return [docutils.nodes.raw('', content, format='html')]

def format_tree(document):
	if isinstance(document, docutils.nodes.Text):
		return document.astext()
	elif isinstance(document, docutils.nodes.reference):
		return {
			'tag' : document.tagname,
			'values' : [document.attributes.get('refuri')]
		}
	else:
		d = {}
		tag = document.tagname
		d['tag'] = tag
		d['values'] = []
		for child in document.children:
			value = format_tree(child)
			d['values'].append(value)
		return d


docutils.parsers.rst.directives.register_directive('template', TemplateDirective)
docutils.parsers.rst.directives.register_directive('math', MathDirective)
docutils.parsers.rst.directives.register_directive('internal', InternalDirective)
docutils.parsers.rst.directives.register_directive('image', ImageDirective)
docutils.parsers.rst.directives.register_directive('figure', FigureDirective)


class DocInfo(object):
	def __init__(self):
		self.errors = None
		self.title = None
		self.tree = None
		self.subtitle = None
		self.meta = None
		self.refs = None
		self.html_parts = None

def publish_text(text, template_callback=None, math_callback=None,
image_callback=None, internal_callback=None, math_pre_callback=None,
**additional_settings):
	'''Publish text into a RestrucutredText HTML document
	
	:parameters:
		text : `unicode`
			The input text
		template_callback
			This function will be called when a template is requested::
			
				def template_callback(`unicode` name):
					return `unicode`
				
		math_callback
			This function will be called when mathematics is created::
			
				def math_callback(md5_hash, image_filename):
					return src
		
		image_callback
			This function will be called when an image is requested::
			
			def image_callback(`unicode` src):
				return `unicode` new_src
		
		internal_callback
			This function will be called for internal procedures::
			
			def internal_callback(*args):
				return `unicode` html
		
		math_pre_callback
			This function is called before generation of math images
			
			def math_pre_callback(md5_hex):
				return src
			
	
	:rtype: `DocInfo`
	'''
	
	error_stream = StringIO.StringIO()
	settings = {
		'halt_level' : 5,
		'warning_stream' : error_stream,
		'file_insertion_enabled' : False,
		'raw_enabled' : False,
		'restpub_callbacks': {
			'template': template_callback,
			'math': math_callback,
			'image': image_callback,
			'internal': internal_callback,
			'pre-math': math_pre_callback,
		},
		'restpub_additional_settings': additional_settings,
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
	
	document = publisher.writer.document
	doc_info = DocInfo()
	doc_info.tree = format_tree(document)
	error_stream.seek(0)
	doc_info.errors = error_stream.read()
	doc_info.title = document.get('title')
	doc_info.subtitle = document.get('subtitle')
	
	if not doc_info.subtitle:
		for element in document:
			if element.tagname == 'subtitle':
				doc_info.subtitle = element.astext()
	
	doc_info.meta = {}
	i = publisher.document.first_child_matching_class(docutils.nodes.docinfo)
	if i is not None:
		docinfo = document[i]
	
		for node in docinfo:
			doc_info.meta[node.tagname] = node.astext()
	
#	doc_info['refs'] = {}
#	for name, node_list in document.refnames.iteritems():
#		doc_info['refs'][name] = map(format_tree, node_list)
	
	doc_info.html_parts = publisher.writer.parts
	
	return doc_info


TexVCInfo = collections.namedtuple('TexVCInfo', 
	['code', 'hash', 'html', 'mathml', 'has_error', 'error_arg'])

def texvc_lexor(s):
	'''Lexes the output from texvc
	
	:rtype: `TexVCInfo`
	'''
	
	code = s[0]
	has_error = code in ('S', 'E', 'F', '-')
	mathml = None
	html = None
	hash = None
	error_arg = None
	
	if code == 'F':
		error_arg = s[1:]
	
	if not has_error:
		hash = s[1:1+32]
	
		if code == 'X':
			mathml = s[33:]
		else:
			html, nul, mathml = s[33:].partition('\x00')
			html = html
			mathml = mathml
			del nul
	
	t = TexVCInfo(code=code, has_error=has_error, mathml=mathml,
		html=html, hash=hash, error_arg=error_arg)
	return t