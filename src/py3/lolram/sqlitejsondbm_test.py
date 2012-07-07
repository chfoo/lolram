'''Test sqlite3 json dbm'''
#
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
import lolram.sqlitejsondbm
import unittest

__docformat__ = 'restructuredtext en'


class TestDB(unittest.TestCase):
    def test_simple(self):
        db = lolram.sqlitejsondbm.Database(':memory:')

        self.assertEqual(0, len(db.keys()))
        self.assertRaises(IndexError, lambda: db['non_existant'])

        d1 = {'some_value': 123}
        db['my_key'] = d1

        self.assertEqual(db['my_key'], d1)

        self.assertEqual(1, len(db.keys()))

        del db['my_key']

        self.assertEqual(0, len(db.keys()))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
