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
import glob
import random

from bitstring.constbitarray import ConstBitArray
from lolram2.respool import FileResPool, FileResource


class FileResPoolOnFilesystem(FileResPool):
	def set_file_dir(self, path):
		self._file_dir = path
		
	def _derive_id(self, hash):
		return (ord(hash[0]), ord(hash[1]) << 8, ord(hash[2]) << 16)
	
	def _derive_hash_hint(self, id):
		return (id & 0xff, (id >> 8) & 0xff, (id >> 16) & 0xff)

	def _get_file_path(self, hash, id):
		# ensure not built-in id()
		assert isinstance(id, (int, long))
		hash_hex = hash.encode('hex').lower()
		
		path = os.path.join(self._file_dir, 
			hash_hex[0:2], 
			hash_hex[2:4], 
			hash_hex[4:6],
			'%s-%s' % (hash_hex, id)
		)
		
		return path
	
	def _find_file_by_id(self, id):
		# ensure not built-in id()
		assert isinstance(id, (int, long))
		hash_hint = self._derive_hash_hint(id)
		pattern = '%s/%02x/%02x/%02x/*-%s' % (self._file_dir, 
			hash_hint[0], hash_hint[1], hash_hint[2], id)
		
		for path in glob.glob(pattern):
			return path
	
	def _find_file_by_hash(self, hash):
		hash_hex = hash.encode('hex').lower()
		
		pattern = os.path.join(self._file_dir, 
			hash_hex[0:2], 
			hash_hex[2:4], 
			hash_hex[4:6],
			'%s-*' % hash_hex
		)
		
		for path in glob.glob(pattern):
			return path
	
	def get_file(self, id):
		path = self._find_file_by_id(id)
		
		if path and os.path.exists(path):
			f = FileResource(path, 'rb')
			f.hash = os.path.basename(path).split('-')[0].decode('hex')
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
		
		path = self._find_file_by_hash(hash)
		
		if path and os.path.exists(path):
			return int(os.path.basename(path).split('-')[-1])
		elif create:
			while True:
				n1, n2, n3 = self._derive_id(hash)
				n4 = ord(os.urandom(1)) << 24
				n5 = ord(os.urandom(1)) << 32
				n6 = ord(os.urandom(1)) << 40
				n7 = ord(os.urandom(1)) << 48
				
				id_num = n1 | n2 | n3 | n4 | n5 | n6 | n7
				
				if not self._find_file_by_id(id_num):
					break
			
			path = self._get_file_path(hash, id_num)
			
			# Make dir if needed
			dirname = os.path.dirname(path)
			
			if not os.path.exists(dirname):
				os.makedirs(dirname)
			
			temp_file = tempfile.NamedTemporaryFile(delete=False)
			
			assert file_obj.tell() == 0
			shutil.copyfileobj(file_obj, temp_file)
			
			# Ensures atomic
			os.rename(temp_file.name, path)
			
			return id_num
		
	
FileResPool.register(FileResPoolOnFilesystem)