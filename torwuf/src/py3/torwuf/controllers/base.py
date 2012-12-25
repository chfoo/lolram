# This file is part of Torwuf.
# Copyright © 2012 Christopher Foo <chris.foo@gmail.com>.
# Licensed under GNU GPLv3. See COPYING.txt for details.
from tornado.web import RequestHandler, HTTPError
import base64
import functools
import http.client
import traceback


class BaseRequestHandler(RequestHandler):
    def write_error(self, status_code, exc_info=None, **kwargs):
        if status_code == http.client.NOT_FOUND:
            self.render('error/not_found.html')
            return

        if exc_info:
            traceback_msg = traceback.format_exception(*exc_info)
        else:
            traceback_msg = ''

        if status_code // 100 == 5:
            self.render('error/error.html', status_code=status_code,
                traceback_msg=traceback_msg)
        else:
            self.render('error/exception.html', status_code=status_code,
                traceback_msg=traceback_msg)

    def get_current_user(self):
        if self.application.testing_key \
        and self.request.headers.get('X-Testing-Key') \
        == self.application.testing_key:
            return 'test:localhost'

        if not hasattr(self.application, '_session_controller'):
            return

        with self.application.session(self, save=False) as s:
            if 'user_email' in s:
                return 'email:{}'.format(s['user_email'])

    def check_xsrf_cookie(self):
        if self.application.testing_key \
        and self.request.headers.get('X-Testing-Key') \
        == self.application.testing_key:
            return

        RequestHandler.check_xsrf_cookie(self)


def require_admin(fn):
    @functools.wraps(fn)
    def wrapper(self, *args, **kargs):
        admin = self.application.config_parser['account']['admin']

        if self.get_current_user() in ('test:localhost', admin):
            return fn(self, *args, **kargs)
        else:
            raise HTTPError(http.client.UNAUTHORIZED)

    return wrapper


def tag_list_to_str(tags):
    '''Convert a list parsed by ``shlex.split()`` to a string'''

    escaped_list = []

    for tag in tags:
        if '"' in tag:
            tag = tag.replace('"', r'\"')

        if ' ' in tag:
            tag = '"%s"' % tag

        escaped_list.append(tag)

    return ' '.join(escaped_list)


def bytes_to_b32low_str(b):
    return str(base64.b32encode(b), 'utf8').rstrip('=').lower()


def b32low_str_to_bytes(s):
    length = len(s)
    if length % 8 != 0:
        s = '%s%s' % (s, '=' * (8 - length % 8))

    return base64.b32decode(s.encode(), True, b'l')
