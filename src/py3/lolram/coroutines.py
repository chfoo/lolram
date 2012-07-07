'''Coroutine helpers'''
#
#	Copyright © 2011-2012 Christopher Foo <chris.foo@gmail.com>
#
#	This file is part of Lolram.
#
#	Lolram is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	Lolram is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with Lolram.  If not, see <http://www.gnu.org/licenses/>.
#
import functools

__docformat__ = 'restructuredtext en'


def coroutine(func):
    '''A decorator function that takes care of starting a coroutine
    automatically on call.

    :See: http://www.dabeaz.com/coroutines/
    '''

    @functools.wraps(func)
    def start(*args, **kwargs):
        cr = func(*args, **kwargs)

        next(cr)

        return cr

    return start
