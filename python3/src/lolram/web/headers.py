'''HTTP header manipulation'''
#
#	Copyright © 2010-2011 Christopher Foo <chris.foo@gmail.com>
#
#	This file is part of Lolram.
#
#	Lolram is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	Lolram is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with Lolram.  If not, see <http://www.gnu.org/licenses/>.
#
import collections

__docformat__ = 'restructuredtext en'

def header_list_to_dict(header_list):
	d = {}
	
	for name, value in header_list:
		if name not in d:
			d[name] = [value]
		else:
			d[name].append(value)
	
	return d

def header_dict_to_list(header_dict):
	l = []
	
	for name, values in header_dict.items():
		for value in values:
			l.append((name, value))
	
	return l

class HeaderListMapper(collections.UserDict):
	'''Lightweight WSGI header list mapping'''
	
	def __init__(self, header_list):
		self.data = header_list_to_dict(header_list)
	
	def get_first(self, name, default=None):
		if name in self.data and self.data[name]:
			return self.data[name][0]
		
		return default
	
	def set_single(self, name, value):
		self.data[name] = [value]
	
	def to_list(self):
		return header_dict_to_list(self.data)

