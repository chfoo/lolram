from pywheel.web.bootstrap import Bootstrap
from torwuf.controllers.app import Application
import argparse
import logging
import tornado.ioloop


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--debug', action='store_true', default=False)
    arg_parser.add_argument('--host', default='127.0.0.1')
    logging.basicConfig(level=logging.INFO)
    bootstrap = Bootstrap(arg_parser=arg_parser)
    app = Application(bootstrap)
    hostname = bootstrap.args.host
    xheaders = hostname == '127.0.0.1'
    app.listen(8798, hostname, xheaders=xheaders)
    tornado.ioloop.IOLoop.instance().start()
