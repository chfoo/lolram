#encoding=utf8

'''Configuration loader'''

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

import os
import ConfigParser

import dataobject

class Config(dataobject.DataObject):
	def populate_section(self, default_section_config):
		if default_section_config.name not in self:
			self[default_section_config.name] = SectionConfig()
		
		for key, value in default_section_config.options.iteritems():
			if key not in self[default_section_config.name]:
				self[default_section_config.name][key] = value
	
class SectionConfig(dataobject.DataObject):
	pass

def load(filename, default_config=None):
	if not os.path.exists(filename):
		return None
	
	config = Config()
	
	if default_config:
		for section, options in default_config.iteritems():
			config[section] = SectionConfig(options)
	
	config_parser = ConfigParser.SafeConfigParser()
	ok_filenames = config_parser.read([filename]) #@UnusedVariable
	
	for section in config_parser.sections():
		if section not in config:
			config[section] = SectionConfig()
		
		for option, value in config_parser.items(section):
			option_ = option.replace('-', '_')
			value_ = value
		
			for fn in ('getboolean', 'getint', 'getfloat'):
				try:
					value_ = getattr(config_parser, fn)(section, option_)
					break
				except ValueError:
					pass
			
			config[section][option_] = value_
	
	return config

class DefaultSectionConfig(object):
	def __init__(self, section_name, **options):
		self.name = section_name
		self.options = options

