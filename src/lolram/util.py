# encoding=utf8

'''Utility functions'''

#	Copyright © 2010–2011 Christopher Foo <chris.foo@gmail.com>

#	Portions under Attribution-ShareAlike 2.5 Generic (CC BY-SA 2.5)

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

__doctype__ = 'restructuredtext en'

import base64
import magic

magic_cookie = magic.open(magic.MAGIC_NONE)
magic_cookie.load()
magic_cookie_mime = magic.open(magic.MAGIC_MIME)
magic_cookie_mime.load() 

def int_to_bytes(n, padding=0):
	s = hex(n)[2:].rstrip('L')
	if len(s) % 2 != 0:
		s = '0%s' % s
	s = s.rjust(padding * 2, '0')
	return s.decode('hex')

def bytes_to_int(s):
	return long(s.encode('hex'), 16)

def bytes_to_b32low(s):
	return base64.b32encode(s).rstrip('=').lower()

def b32low_to_bytes(s):
	length = len(s)
	if length % 8 != 0:
		s = '%s%s' % (s, '=' * (8 - length % 8))
	
	return  base64.b32decode(str(s), True, 'l')
