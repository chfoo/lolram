# encoding=utf8

'''Store on the filesystem'''

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

FILE_MAX = 32 ** 8 - 1
FILE_DIR_HASH = 997

import os
import hashlib
import os.path
import tempfile
import shutil

from bitstring.constbitarray import ConstBitArray
from lolram2.respool import FileResPool, FileResource


class FileResPoolOnFilesystem(object):
	def set_file_dir(self, path):
		self._file_dir = path

	def _get_file_path(self, id):
		# ensure not built-in id()
		assert isinstance(id, int) or isinstance(id, long)
		hash = hashlib.sha256(ConstBitArray(length=256, int=id).bytes).digest()
		hash_hex = hash.encode('hex').lower()
		
		path = os.path.join(self._file_dir, 
			hash_hex[0:4], 
			hash_hex[4:8], 
			hash_hex[8:12],
			hash_hex[12:]
		)
		
		return path
	
	def get_file(self, id):
		path = self._get_file_path(id)
		
		if os.path.exists(path):
			f = FileResource(path, 'rb')
			f.hash = hashlib.sha256(ConstBitArray(length=256, int=id).bytes).digest()
			f.filename = path
			return f
	
	def set_file(self, file_obj, create=True):
		sha256_obj = hashlib.sha256()
		
		while True:
			s = file_obj.read(2**12)
			
			if s == '':
				break
			
			sha256_obj.update(s)
		
		# FIXME: don't rely on seek operation
		file_obj.seek(0)
		
		hash = sha256_obj.digest()
		id_num = ConstBitArray(bytes=hash).int
		
		path = self._get_file_path(id_num)
		
		if os.path.exists(path):
			return id_num
		elif create:
			# Make dir if needed
			dirname = os.path.dirname(path)
			
			if not os.path.exists(dirname):
				os.makedirs(dirname)
			
			temp_file = tempfile.NamedTemporaryFile(delete=False)
			
			assert file_obj.tell() == 0
			shutil.copyfileobj(file_obj, temp_file)
			
			# Ensures atomic
			os.rename(temp_file.name, path)
			
			return ConstBitArray(bytes=hash).int
		
	
FileResPool.register(FileResPoolOnFilesystem)