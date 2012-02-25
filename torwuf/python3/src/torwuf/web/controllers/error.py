'''Error handler'''
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
import http.client
import traceback
import logging
import sys
_logger = logging.getLogger(__name__)

class ErrorOutputHandlerMixin(object):
	def write_error(self, status_code, exc_info=None, **kwargs):
		status_msg = http.client.responses.get(status_code, '')
		template_name = 'error/server_error.html'
		
		if status_code == 404:
			template_name = 'error/not_found_error.html'
		
		elif 400 <= status_code < 500:
			template_name = 'error/client_error.html'
			
		if exc_info:
			try:
				traceback_str = '\n'.join(traceback.format_exception(*exc_info))
			except:
				_logger.exception('Exception during formatting exception')
				traceback_str = '(Error during formatting exception)'
		else:
			traceback_str = ''
		
		if self.controller.config.config_parser.getboolean('logging', 
		'stack_trace_to_stderr', fallback=False):
			sys.stderr.write(traceback_str)
		
		self.render(template_name, status_code=status_code, 
			status_msg=status_msg, traceback_str=traceback_str)
		