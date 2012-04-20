'''The root path (/) controller'''
#
#	Copyright (c) 2012 Christopher Foo <chris.foo@gmail.com>
#
#	This file is part of Torwuf.
#
#	Torwuf is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	Torwuf is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with Torwuf.  If not, see <http://www.gnu.org/licenses/>.
#
import http.client
import tornado.web
import torwuf.web.controllers.base

class IndexController(torwuf.web.controllers.base.BaseController):
	def init(self):
		self.add_url_spec(r'/', IndexRequestHandler)
		self.add_url_spec(r'/dummy.fcgi/(.*)', MisconfiguredDummyAppHandler)
		self.add_url_spec(r'/z/(.*)', MissingStaticFilesHandler)
		self.add_url_spec(r'/about', AboutHandler)
		self.add_url_spec(r'/(.*)', CatchAllRequestHandler)

class IndexRequestHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'index'
	
	def get(self):
		self.render('index/index.html')
		

class AboutHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'about'
	
	def get(self):
		self.render('index/about.html')

class CatchAllRequestHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'catch_all'
	
	def get(self, arg):
		handlers = self.app_controller.wsgi_application._get_host_handlers(self.request)
		path = self.request.path
		
		if path.endswith('/'):
			path = path.rstrip('/')
		else:
			path = '%s/' % path
		
		for spec in handlers:
			match = spec.regex.match(path)
			if match and spec.name != CatchAllRequestHandler.name:
				self.set_status(http.client.MULTIPLE_CHOICES)
				self.render('index/disambig.html', path=path)
				return
					
		raise tornado.web.HTTPError(http.client.NOT_FOUND)
	
					

class MisconfiguredDummyAppHandler(torwuf.web.controllers.base.BaseHandler):
	# XXX: might want to fix this in the lighttpd config
	
	name = 'misconfigured_dummy_app'
	
	def get(self, arg):
		self.redirect('/%s' % arg, permanent=True)

class MissingStaticFilesHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'missing_static_files'
	
	def get(self, arg):
		raise tornado.web.HTTPError(500, 
			'Static file directory missing? Not in production mode?')