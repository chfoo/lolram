# encoding=utf8

'''Reads data from Unicode.org's unihan.zip'''

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

import string
import sys
import json

def readings(filename='Unihan_Readings.txt'):
	f = open(filename, 'rb')
	
	t = [None, {}]
	
	for line in f:
		if not line.strip() or line.startswith('#'):
			continue
		
		glyph_code, key_name, value = line.split('\t')
		
		if t[0] != glyph_code_to_unichr(glyph_code) and t[0] is not None:
			yield t
			t = [None, {}]
		
		t[0] = glyph_code_to_unichr(glyph_code)
		t[1][key_name] = value.rstrip('\n\r').decode('utf8')

	yield t

SAFE_GLYPH_CHARS = string.hexdigits + 'U+'

def glyph_code_to_unichr(s):
	for c in s:
		if c not in SAFE_GLYPH_CHARS:
			return None
	
	s = s.replace('U+', '0x')
	
	return unichr(eval(s))

if __name__ == '__main__':
	if sys.argv[1] == 'readings':
		for t in readings():
			d = dict(t[1])
			d['_id'] = t[0]
			
			sys.stdout.write(json.dumps(d))
			sys.stdout.write('\n')
