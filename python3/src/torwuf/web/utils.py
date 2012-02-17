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
import logging

_logger = logging.getLogger(__name__)

class StripDummyAppPath(object):
	def __init__(self, app):
		self.app = app
	
	def __call__(self, environ, start_response):
		new_script_name = environ['SCRIPT_NAME'].replace(
			'/dummy.fcgi', '')
		new_path_info = environ['REQUEST_URI'].split('?', 1)[0]
		
		_logger.debug('SCRIPT_NAME %s to %s', environ['SCRIPT_NAME'], new_script_name)
		_logger.debug('PATH_INFO %s to ', environ['PATH_INFO'], new_path_info)
		_logger.debug('REQUEST_URI %s', environ.get('REQUEST_URI'))
		
		environ['SCRIPT_NAME'] = new_script_name
		environ['PATH_INFO'] = new_path_info
		return self.app(environ, start_response)
