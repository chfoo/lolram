'''String resources and constants'''
#
#    Copyright (c) 2012 Christopher Foo <chris.foo@gmail.com>
#
#    This file is part of Torwuf.
#
#    Torwuf is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Torwuf is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Torwuf.  If not, see <http://www.gnu.org/licenses/>.
#
import bson.code

MAP_TAGS = ("function () {"
    "  this.%s.forEach(function(z) {"
    "    emit(z, 1);"
    "  });"
    "}")

REDUCE_TAGS = ("function (key, values) {"
    "  var total = 0;"
    "  for (var i = 0; i < values.length; i++) {"
    "    total += values[i];"
    "  }"
    "  return total;"
    "}")


def make_map_tags_code(key_name='tags'):
    return bson.code.Code(MAP_TAGS % key_name)


def make_reduce_tags_code():
    return bson.code.Code(REDUCE_TAGS)
