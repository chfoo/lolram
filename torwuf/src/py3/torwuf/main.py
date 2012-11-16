from pywheel.web.bootstrap import Bootstrap
from torwuf.controllers.app import Application
import tornado.ioloop


def main():
    bootstrap = Bootstrap()
    app = Application(bootstrap)
    app.listen(8798, 'localhost')
    tornado.ioloop.IOLoop.instance().start()
