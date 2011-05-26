# encoding=utf8

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

'''JSON and XML serializer

The use of this component will allow serialization of ``fardel.data``
to common formats. To request data in these formats, include the 
query parameter ``format=[type]``, where ``[type]`` is the
requested format, in the URL.

'''
__doctype__ = 'restructuredtext en'

import base

from .. import serializer

class SerializerAgent(base.BaseComponentAgent):
	JSON = 'json'
	XML = 'xml'
	HTML = 'html'
	RSS = 'rss'
	
	def render(self, fardel):
		format = fardel.req.url.query.getfirst('format')
		return self.serialize(fardel, fardel.data, format=format)
	
	def serialize(self, fardel, data, format='json'):
		'''Serialize the data
		
		:parameters:
			data
				Data
			format
				Format
		'''
		
		if format == self.JSON:
			return serializer.serialize_json(data)
		elif format == self.XML:
			return serializer.serialize_xml(data)
		

class SerializerManager(base.BaseComponentManager):
	agent_class = SerializerAgent
	name = 'serializer'



