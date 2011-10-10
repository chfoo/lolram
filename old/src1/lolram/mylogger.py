# encoding=utf8

'''Logging'''

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


import logging
import logging.handlers

ESC = 0x1b
_logger = None
_settings = {
	'enable_console' : True,
	'enable_file' : False,
	'file_dest_dir' : None,
}

def console_handler(): 
	handler = logging.StreamHandler()
	handler.setLevel(logging.DEBUG)
	formatter = logging.Formatter(u"\x1b[0m\x1b[2m"
		u"%(name)s:%(module)s:%(lineno)d:%(levelname)s"
		u"\x1b[0m %(message)s")
	handler.setFormatter(formatter)

	return handler

def file_handler(dest_dir):
	handler = logging.handlers.RotatingFileHandler(dest_dir, maxBytes=1048576,
		backupCount=9)
	handler.setLevel(logging.DEBUG)
	formatter = logging.Formatter(u"%(asctime)s "
			u"%(name)s:%(module)s:%(lineno)d:%(levelname)s %(message)s")
	handler.setFormatter(formatter)
	
	return handler

_console_handler = console_handler()

def get_logger():
	global _logger
	
	if _logger is None:
		logger = logging.getLogger('lolram')
		logger.setLevel(logging.DEBUG)
	
		logger.addHandler(_console_handler)
		
		_logger = logger
	
	return _logger

