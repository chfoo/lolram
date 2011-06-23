# encoding=utf8

'''URL path functions'''

#	This file includes portions from wsgiref.util
#	   Copyright © 2001-2010 Python Software Foundation; All Rights Reserved

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

import wsgiref.util
import urllib

def common(path_a, path_b):
	'''Get the common base path of paths
	
	:returns: `tuple`
		1. `str` common prefix
		2. `str` remaining path of `path_a`
		3. `str` remaining path of `path_b`
	
	:rtype: `tuple`
	'''
	parts_a = path_a.strip('/').split('/')
	parts_b = path_b.strip('/').split('/')
	
	i = 0
	while i < len(parts_a) and i < len(parts_b):
		if parts_a[i] == parts_b[i]:
			i += 1
		else:
			break
	
	common = '/'.join(parts_a[:i])
	a = '/'.join(parts_a[i:])
	b = '/'.join(parts_b[i:])
	return (common, a, b)
	
def application_uri(environ):
    """Return the application's base URI (no PATH_INFO or QUERY_STRING)
    
    This version of `wsgiref.util.request_uri` does not incorrectly qoute
    the ``;`` parameter notation.
    """
    url = environ['wsgi.url_scheme']+'://'
#    from urllib import quote

    if environ.get('HTTP_HOST'):
        url += environ['HTTP_HOST']
    else:
        url += environ['SERVER_NAME']

        if environ['wsgi.url_scheme'] == 'https':
            if environ['SERVER_PORT'] != '443':
                url += ':' + environ['SERVER_PORT']
        else:
            if environ['SERVER_PORT'] != '80':
                url += ':' + environ['SERVER_PORT']

    url += urllib.quote(environ.get('SCRIPT_NAME') or '/', '/;')
    return url


def request_uri(environ, include_query=1):
    """Return the full request URI, optionally including the query string
    
    This version of `wsgiref.util.request_uri` does not incorrectly qoute
    the ``;`` parameter notation.
    """
    url = application_uri(environ)
#    from urllib import quote
    path_info = environ.get('PATH_INFO','')
    if not environ.get('SCRIPT_NAME'):
        url += path_info[1:]
    else:
        url += path_info
    if include_query and environ.get('QUERY_STRING'):
        url += '?' + environ['QUERY_STRING']
    return url
