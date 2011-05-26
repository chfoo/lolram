# encoding=utf8

'''Config loader testing'''

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

__doctype__ = 'restructuredtext en'

import unittest
import os.path

import lolram.configloader as configloader

class TestDataObject(unittest.TestCase):
	def setUp(self):
		self.confpath = os.path.abspath(os.path.join(
			os.path.dirname(__file__),
			'testconfig.conf')
		)
		self.badpath = 'nonexistant-path.conf'
		
	def test_load_and_get(self):
		'''It should load and get options and not error if option is not 
		specified in file'''
		
		config = configloader.load(self.confpath)
		self.assertTrue(config)
		
		self.assertTrue('sec1' in config)
		self.assertEqual(config.sec1.opt1, 'val1')
		self.assertEqual(config.sec1.opt2, True)
		self.assertEqual(config.sec1.opt3, 12)
		self.assertEqual(config.sec1.opt4, 12.4)
		self.assertEqual(config.sec1.opt5.split(), ['a','b','c','d','e','f'])
		self.assertEqual(config.sec2.kittens, True)
		self.assertFalse(config.secNonExistant)
	
	def test_bad_load(self):
		'''It should return `None` if config path is non-existant'''
		
		config = configloader.load(self.badpath)
		self.assertFalse(config)
	
	def test_default_opts(self):
		'''It should interpolate default options specified passed into 
		function'''
		
		config = configloader.load(self.confpath, {
			'sec2': {
				'kittens' : False,
				'puppies' : False,
			}
		})
		self.assertTrue(config)
		
		self.assertEqual(config.sec2.kittens, True)
		self.assertEqual(config.sec2.puppies, False)
	
	def test_default_section_opts(self):
		'''It should interpolate default section options after getting config.
		It should not overwrite options with default values'''
	
		sec2 = configloader.DefaultSectionConfig('sec2', kittens=False,
			puppies=False)
		sec3 = configloader.DefaultSectionConfig('sec3', a='b',
			f=3.0)
		
		config = configloader.load(self.confpath)
		config.populate_section(sec2)
		config.populate_section(sec3)
		self.assertTrue(config)
		
		self.assertEqual(config.sec2.kittens, True)
		self.assertEqual(config.sec2.puppies, False)
		self.assertEqual(config.sec3.a, 'b')
		self.assertEqual(config.sec3.f, 3.0)
		
		
		
