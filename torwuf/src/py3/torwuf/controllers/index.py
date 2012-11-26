# This file is part of Torwuf.
# Copyright © 2012 Christopher Foo <chris.foo@gmail.com>.
# Licensed under GNU GPLv3. See COPYING.txt for details.
from torwuf.controllers.authentication import SimpleGoogleLoginHandler
from torwuf.controllers.base import BaseRequestHandler
import http.client
import tornado.web


class IndexHandler(BaseRequestHandler):
    def get(self):
        self.render('index/index.html')


class CatchAllHandler(BaseRequestHandler):
    def get(self, *args):
        raise tornado.web.HTTPError(http.client.NOT_FOUND)

    def post(self, *args):
        self.get(*args)


class AboutHandler(BaseRequestHandler):
    def get(self):
        self.render('index/about.html')


class ProjectsHandler(BaseRequestHandler):
    def get(self):
        self.render('index/projects.html')


class SiteMapHandler(BaseRequestHandler):
    def get(self):
        self.render('index/site_map.html')


class MissingStaticFilesHandler(BaseRequestHandler):
    def get(self, arg):
        raise tornado.web.HTTPError(500,
            'Static file directory missing? Not in production mode?')


class CatSignalHandler(BaseRequestHandler):
    def get(self):
        self.render('index/catsignal.html')


url_specs = (
    (r'/', IndexHandler),
    (r'/about', AboutHandler),
    (r'/projects', ProjectsHandler),
    (r'/site_map', SiteMapHandler),
    (r'/simple_google_login', SimpleGoogleLoginHandler),
    (r'/cat-signal', CatSignalHandler),
    (r'/z/(.*)', MissingStaticFilesHandler,)
    # Catch all is added by application at the end
)
