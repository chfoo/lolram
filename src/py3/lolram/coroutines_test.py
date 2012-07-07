#    Copyright © 2011-2012 Christopher Foo <chris.foo@gmail.com>
#
#    This file is part of Lolram.
#
#    Lolram is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Lolram is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Lolram.  If not, see <http://www.gnu.org/licenses/>.
#

import lolram.coroutines
import unittest


def my_undec_coroutine():
    while True:
        (yield)


@lolram.coroutines.coroutine
def my_coroutine():
    while True:
        (yield)


class TestCoroutine(unittest.TestCase):
    def test_failure(self):
        '''It should not automatically start the coroutine'''

        c = my_undec_coroutine()

        def f():
            c.send('asdf')

        self.assertRaises(TypeError, f)

    def test_coroutine(self):
        '''It should automatically start the coroutine'''

        c = my_coroutine()
        c.send('asdf')

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
