# encoding=utf8

'''Support for showing messages to the user'''

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

import tornado.web
import tornado.escape

class MessageMixIn(object):
	def prepare(self):
		self._message_model = Message()
	
	@property
	def message(self):
		return self._message_model
	
#	def update_render_kargs(self, kargs):
#		kargs['messages'] = self._message_model


class Message(list):
	def add(self, title, msg=None, class_=None, icon=None):
		self.append((title, msg, icon, class_))


class MessageUIModule(tornado.web.UIModule):
	def render(self, messages=None):
		if messages is None:
			messages = self.handler.message
		
		buf = cStringIO.StringIO()
		
		buf.write('<aside class="messageModule">')
		
		for title, msg, icon, class_ in messages:
			buf.write('<div class="messageBox">')
			buf.write('<div class="messageTitle">')
			buf.write(tornado.escape.xhtml_escape(title.encode('utf8')))
			buf.write('</div>')
			
			if msg:
				buf.write('<p>')
				buf.write(tornado.escape.xhtml_escape(msg.encode('utf8')))
				buf.write('</p>')
			buf.write('</div>')
			
		buf.write('</aside>')
		
		buf.seek(0)
		return buf.read()