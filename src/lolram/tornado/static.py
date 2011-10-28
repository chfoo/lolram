# encoding=utf8

'''Support for sending files'''

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

import datetime
import os.path
import mimetypes

HTTP_TIME_PARSE_STR = '%a, %d %b %Y %H:%M:%S %Z'
HTTP_TIME_FORMAT_STR = '%a, %d %b %Y %H:%M:%S GMT'

class StaticFileHandlerMixIn(object):
	CHUNK_SIZE = 4096
	
	def output_file(self, path, download_filename=None, content_type=None):
		self.set_header('X-Sendfile', path)
		
		last_modified = datetime.datetime.utcfromtimestamp(
			os.path.getmtime(path))
		
		mt = content_type or self.headers.get('content-type')
		
		if not mt:
			mtt = mimetypes.guess_type(download_filename or path)
			
			if mtt:
				mt = mtt[0]
		
		if mt:
			self.set_header('Content-Type', mt)
		
		# Need 1 second precision (in case filesystems that support 
		# microseconds since we only transmit 1 second precision
		# Otherwise, we get a bug comparing dates
		last_modified = last_modified.replace(
			last_modified.year,
			last_modified.month,
			last_modified.day,
			last_modified.hour,
			last_modified.minute,
			last_modified.second,
			0
		)
		self.set_header('Accept-Ranges', 'bytes')
		self.set_header('Last-Modified', last_modified.strftime(
			HTTP_TIME_FORMAT_STR))
		
		if_modified_since = self.request.headers.get('If-Modified-Since')
		if if_modified_since:
			if_modified_since = datetime.datetime.strptime(
				if_modified_since, HTTP_TIME_PARSE_STR)
		
			# 304 not modified feature
			if last_modified <= if_modified_since:
				self.set_status(304)
				del self._headers['Content-Type']
				return
		
		if download_filename:
			self.set_header('Content-Disposition',
				u'attachment; filename=%s' % download_filename)
		
		# There is a request for a partial file
		http_range = self.request.headers.get('Range')
		if http_range and 'bytes' in http_range:
			range_type, range_value = http_range.split('=')
			range_lower, range_upper = range_value.split('-')
			
			if range_lower:
				range_lower = int(range_lower)
			else:
				range_lower = 0
			
			if range_upper:
				range_upper = int(range_upper)
			else:
				range_upper = os.path.getsize(path)
			
			self.set_status(206)
		else:
			range_lower = 0
			range_upper = os.path.getsize(path)
		
		range_size = range_upper - range_lower
		
		self.set_header('Content-Length', str(range_size))
		
		bytes_left = range_size
		with open(path, 'rb') as f_obj:
			f_obj.seek(range_lower)
		
			while True:
				bytes_left = max(0, bytes_left)
				data = f_obj.read(min(bytes_left, self.CHUNK_SIZE))
			
				if data == '':
					break
			
				bytes_left -= self.READ_SIZE
				
				self.write(data)
				self.flush()
		