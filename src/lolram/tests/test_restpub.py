# encoding=utf8

'''reStructuredText publisher testing'''

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

import unittest

from lolram import restpub

TEMPLATE_1 = u'''
aaa {{0}} bbb {{1}} {{0}} ccc {{val1}} ddd {{val2}} 

aa{{0}}aa

'''

TEXT_1 = u'''
######################################
Document Title
######################################
======================================
Document Subtitle
======================================


:Author: author name
:Date: 2000 01 01 01:01:01
:copyright: asdf

Lorem ipsum *dolor* sit amet, **consectetur** adipiscing elit. ``Nam id odio`` nec risus pellentesque rhoncus. Etiam rutrum neque nec arcū fermentum sodales. Aliquam eleifend félis quis turpis viverra sagittis. Donec sodales, dolor in ultricies volutpat, nisl velit vulputate ligula, in ultricies purus lorem eu lectus. Vivamus nunc eros, tincidunt ac venenatis at, pọrta vitae lacus. 

Heading
========

Etiam eu massa quis šem tempus congue. Integer egestas gravida volutpat. In consectetur, ligula in blandit pellentesque, orci diam varius augue, eget egestas tortor enim non sem. Sed nunc odio, tristique non pulvinar eget, fringilla fermentum lectus.

Subtitle
---------

Aenean aliquet libero et diam dignissim tempus nec eget ante. Nunc suscipit velit id ligula tincidunt interdum. Aliquam sollicitudin pretium dui, nec ullamcorper diam rhõncus vitae. Mauris sit amet diam et urna venenatis facilisis. Integer cursus vulputate dolor a eleifend.

Heading 2
=========

Subtitle 2
----------

Etiam eu massa quis šem tempus congue. Integer egestas gravida volutpat. In consectetur, ligula in blandit pellentesque, orci diam varius augue, eget egestas tortor enim non sem. Sed nunc odio, tristique non pulvinar eget, fringilla fermentum lectus.

External hyperlinks, like Python_.

.. _Python: http://www.python.org/

Subsubtitle 2
``````````````

Aenean aliquet libero et diam dignissim tempus nec eget ante. Nunc suscipit velit id ligula tincidunt interdum. Aliquam sollicitudin pretium dui, nec ullamcorper diam rhõncus vitae. Mauris sit amet diam et urna venenatis facilisis. Integer cursus vulputate dolor a eleifend. [CIT2002]_

.. [CIT2002] A citation 
   (as often used in journals).

1. asdf asdf
2. jakfjasldf
3. asdjfklsdf

* asdjfklasdf [5]_

.. [5] A numerical footnote. Note 
   there's no colon after the ``]``.
  

============== ==============
a              b
============== ==============
asjfklas       adsfjkdf
jdfjasdf       jaskdfas
asjdfksd       asdfjaskdf 
============== ==============

----

asdf::
	
	asjdfkla jsdfkljaskdf askldf jaskdfj asd
	 asdjfkas djflsdaklf jsdklf asd 
	 fasd d sfdaj fkasdf 
	       




'''


TEXT_2 = u'''

asdf

.. template:: template1
	:0:AAAAA
	:1:BBBBB
	:val1: ZZZZZZZZZ
	
	
ddd


'''

TEXT_3 = ur'''

.. math::
	\pi

'''

TEXT_4 = ur'''

.. math::
	\lim_{n = 0}^{\infty} x 

'''

TEXT_5 = u'''
.. template:: template2
	:2: OOOOOOOOOOO
'''

class TestRestPub(unittest.TestCase):
	def setUp(self):
		def template_lookup_fn(name):
			if name == 'template1':
				return TEMPLATE_1
		
		def math_callback_fn(filename):
			return filename
		
		restpub.template_callback = template_lookup_fn
		restpub.math_callback = math_callback_fn
	
	def my_test_doc_info(self, doc_info):
		self.assertTrue(doc_info)
#		self.assertTrue('tree' in doc_info)
#		self.assertTrue('errors' in doc_info)
		self.assertFalse(doc_info.errors)
	
	def test_doc_publish(self):
		doc_info = restpub.publish_text(TEXT_1)
		self.my_test_doc_info(doc_info)
		self.assertEqual(doc_info.title, u'Document Title')
		self.assertEqual(doc_info.meta['author'], u'author name')
	
	def test_template(self):
		doc_info = restpub.publish_text(TEXT_2)
		self.my_test_doc_info(doc_info)
		self.assertEqual(unicode(doc_info.tree).find('{{0}}'), -1)
		self.assertEqual(unicode(doc_info.tree).find('{{1}}'), -1)
		self.assertNotEqual(unicode(doc_info.tree).find('AAAAA'), -1)
		self.assertNotEqual(unicode(doc_info.tree).find('BBBBB'), -1)
		self.assertNotEqual(unicode(doc_info.tree).find('ZZZZZZZZZ'), -1)
	
	def test_nonexistng_template(self):
		doc_info = restpub.publish_text(TEXT_5)
		self.assertTrue(doc_info.errors)
	
#	def test_template_func(self):
#		self.assertRaises(NotImplementedError, lambda: self.pub2.publish(TEXT_1))
		
	def test_simple_math(self):
		doc_info = restpub.publish_text(TEXT_3)
		self.my_test_doc_info(doc_info)
		self.assertNotEqual(unicode(doc_info.tree).find(u'&pi'), -1)
	
	def test_complex_math(self):
		doc_info = restpub.publish_text(TEXT_4)
		self.my_test_doc_info(doc_info)
		self.assertNotEqual(unicode(doc_info.tree).find(u'image'), -1)
	
	
		
		
		
		
		
		
		
		
		
		
		
		
