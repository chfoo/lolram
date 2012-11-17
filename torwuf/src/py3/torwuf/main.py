from pywheel.web.bootstrap import Bootstrap
from torwuf.controllers.app import Application
import tornado.ioloop
import logging


def main():
    logging.basicConfig(level=logging.INFO)
    bootstrap = Bootstrap()
    app = Application(bootstrap)
    hostname = 'localhost'
    xheaders = hostname == 'localhost'
    app.listen(8798, hostname, xheaders=xheaders)
    tornado.ioloop.IOLoop.instance().start()
