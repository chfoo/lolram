# encoding=utf8

'''Resource optimizer'''

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

import cStringIO
import glob

def optimize(filenames, format='js'):
	output = cStringIO.StringIO()
	
	for p in filenames:
		if format == 'js':
			output.write(';\n')
		
		output.write(u'/* %s */\n' % p)
		
		f = open(p, 'rb')
		output.write(f.read())
		f.close()
	
	output.seek(0)
	
	return output

def optimize_dir(dirname, **kargs):
	g = '%s/*.%s' % (dirname, kargs['format'])
	return optimize(sorted(glob.iglob(g)), **kargs)
	
