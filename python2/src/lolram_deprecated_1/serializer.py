#encoding=utf8

'''Serializer'''

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

__docformat__ = 'restructuredtext en'

SPOOL_FILE_SIZE = 1048576

import tempfile
import json
import wsgiref.util

from lxml import etree

def serialize_json(data, spool_file_size=SPOOL_FILE_SIZE, indent=2, **kargs):
	'''Serialize to JSON format'''
	
	fo = tempfile.SpooledTemporaryFile(max_size=spool_file_size)
	json.dump(data, fo, indent=indent, **kargs)
	fo.seek(0)
	return wsgiref.util.FileWrapper(fo)

def serialize_xml(data, **kargs):
	'''Serialize to XML format'''
	tree = etree.ElementTree()
	tree._setroot(make_xml_fragment(data))
	
	return render_element_tree(tree, **kargs)

def make_xml_fragment(data, object_name='object', array_name='array',
string_name='string', number_name='number', true_name='true',
false_name='false', null_name='null'):
	'''Convert object to xml format'''
	
	if isinstance(data, dict) or hasattr(data, 'iteritems'):
		object_element = etree.Element(object_name)
		
		for key, value in data.iteritems():
			property_element = etree.SubElement(object_element, 'property')
			key_element = etree.SubElement(property_element, 'key')
			key_element.text = key
			property_element.append(make_xml_fragment(value))
		
		return object_element
	elif isinstance(data, list) or hasattr(data, '__iter__'):
		e = etree.Element(array_name)
		for value in data:
			e.append(make_xml_fragment(value))
		return e
	elif isinstance(data, str) or isinstance(data, unicode):
		e = etree.Element(string_name)
		e.text = data
		return e
	elif isinstance(data, int) or isinstance(data, float):
		e = etree.Element(number_name)
		e.text = str(data)
		return e
	elif isinstance(data, bool):
		if data:
			return etree.Element(true_name)
		else:
			return etree.Element(false_name)
	else:
		return etree.Element(null_name)

def render_html_element(element, **kargs):
	tree = etree.ElementTree()
	tree._setroot(element)
	return render_element_tree(tree, **kargs)

def render_element_tree(tree, format='xml', spool_file_size=SPOOL_FILE_SIZE, #@ReservedAssignment
pretty_print=True, doctype=True, html_padding=True):
	'''Render lxml.etree document'''
	
	fo = tempfile.SpooledTemporaryFile(max_size=spool_file_size)
	
	if format == 'html':
		tree.write(fo, encoding='utf-8', method=format, pretty_print=True)
		
		# FIXME: lxml should output the HTML 5 doctype
		# Overwrite the HTML 4 doctype with the HTML 5 doctype
		pos = fo.tell()
		fo.seek(0)
		fo.write(' ' * len(tree.docinfo.doctype))
		fo.seek(0)
		if doctype:
			fo.write('<!DOCTYPE HTML>')
		fo.seek(pos)
		
		if html_padding:
			# Browsers will display web page instead of friendly error page
			# if page is larger than 1k
			if pos < 1024:
				fo.write('<!--')
				fo.write('Kitteh ' * ((1024 - pos) // 7))
				fo.write('-->')
	else:
		tree.write(fo, encoding='utf-8', method=format, xml_declaration=doctype,
			pretty_print=pretty_print)
	
	fo.seek(0)
	
	return wsgiref.util.FileWrapper(fo)

