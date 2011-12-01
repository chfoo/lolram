# encoding=utf8

'''Files'''
import os

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

import contextlib

@contextlib.contextmanager
def safe_writer(path, mode='wb', backup=True):
	'''Writes new version of files safely'''
	
	new_temp_path = u'%s~new~' % path
	f = open(new_temp_path, mode)
	
	yield f
	
	f.close()
	os.rename(new_temp_path, path)