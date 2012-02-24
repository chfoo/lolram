'''Misc functions'''
#
#	Copyright (c) 2012 Christopher Foo <chris.foo@gmail.com>
#
#	This file is part of Torwuf.
#
#	Torwuf is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	Torwuf is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with Torwuf.  If not, see <http://www.gnu.org/licenses/>.
#
import base64

def tag_list_to_str(tags):
	'''Convert a list parsed by ``shlex.split()`` to a string'''
	
	escaped_list = []
	
	for tag in tags:
		if '"' in tag:
			tag = tag.replace('"', r'\"')
		
		if ' ' in tag:
			tag = '"%s"' % tag
		
		escaped_list.append(tag)
	
	return ' '.join(escaped_list)

def bytes_to_b32low_str(b):
	return str(base64.b32encode(b), 'utf8').rstrip('=').lower()

def b32low_str_to_bytes(s):
	length = len(s)
	if length % 8 != 0:
		s = '%s%s' % (s, '=' * (8 - length % 8))
	
	return  base64.b32decode(s.encode(), True, 'l')