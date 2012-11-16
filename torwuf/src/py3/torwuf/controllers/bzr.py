'''Simple BZR repositories over HTTP controllers'''
# This file is part of Torwuf.
# Copyright © 2012 Christopher Foo <chris.foo@gmail.com>.
# Licensed under GNU GPLv3. See COPYING.txt for details.
from pywheel.backoff import Trier
from pywheel.db import sqlitejsondbm
from tornado.httpclient import HTTPRequest
from tornado.web import URLSpec
from torwuf.controllers.base import BaseRequestHandler
import base64
import functools
import hashlib
import http.client
import logging
import os.path
import random
import shutil
import string
import subprocess
import threading
import time
import tornado.web
import wsgiref.util


_logger = logging.getLogger(__name__)


class LoggerheadThread(threading.Thread):
    def __init__(self, controller, port):
        threading.Thread.__init__(self)
        self.isDaemon = True
        self.controller = controller
        self.port = port
        self.name = '{}:{}'.format(__name__, LoggerheadThread.__name__)

        self.init_log_dir()
        self.init_process()

    def init_log_dir(self):
        self.log_dir = os.path.join(self.controller.application.root_path,
             'logs', 'bzr')

        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def init_process(self):
        self.process = subprocess.Popen(['serve-branches',
            '--prefix', '/bzr/repo/',
            self.controller.repo_path,
            '--allow-writes', '--host', 'localhost',
            '--port', str(self.port),
            '--log-folder', self.log_dir,
            '--log-level', 'info',
        ])

    def run(self):
        returncode = self.process.wait()

        if returncode != 0:
            raise Exception(
                'starting loggerhead failed (exit return code {})'.format(
                    returncode))


# It is a bit naive and vulernable to DoS attacks
class LoginRateLimitController(object):
    KEY_TIMESTAMPS = 'timestamps'
    KEY_WHITELIST = 'whitelist'

    def __init__(self, application):
        self.application = application

        def init_db():
            if self.application.db:
                self.collection = self.application.db.login_rate_limit
                return True

        self._trier = Trier(init_db)

    def record_login(self, namespace, username, remote_address, limit=5):
        id_ = '%s/%s' % (namespace, username)
        result = self.collection.find_one({'_id': id_})
        past_hour = time.time() - 3600

        if result:
            if remote_address in result.get(
            LoginRateLimitController.KEY_WHITELIST, []):
                return True

            timestamps = result.get(LoginRateLimitController.KEY_TIMESTAMPS,
                [])
            timestamps = list(filter(lambda t: t >= past_hour, timestamps))

            if len(timestamps) >= limit:
                return False
            else:
                timestamps.append(time.time())
        else:
            timestamps = [time.time()]

        self.collection.save({
            '_id': id_,
            LoginRateLimitController.KEY_TIMESTAMPS: timestamps,
        })

        return True

    def whitelist_login(self, namespace, username, remote_address):
        id_ = '%s/%s' % (namespace, username)
        result = self.collection.find_one({'_id': id_})

        addresses = result.get(LoginRateLimitController.KEY_WHITELIST, [])

        if remote_address in addresses:
            return

        addresses.append(remote_address)
        addresses = addresses[:5]

        self.collection.save({
            '_id': id_,
            LoginRateLimitController.KEY_WHITELIST: addresses,
        })


class InvalidUsernameError(Exception):
    pass


class DBKeys(object):
    USERNAME = 'username'
    HASHED_PASSWORD_1 = 'password1'
    HASHED_PASSWORD_2 = 'password2'
    PASSWORD_1_TIMESTAMP = 'pwTimestamp1'
    REPO_READWRITE_LIST = 'repoRWList'


class BzrController(object):
    VALID_USERNAME_SET = frozenset(string.ascii_lowercase) \
        | frozenset(string.digits)
    VALID_PASSWORD_SET = frozenset(string.printable)

    def __init__(self, application):
        self.application = application
        self.load_config()
        self.init_repos()
        self.init_loggerhead()
        self.init_user_database()
        self.login_rate_limit_controller = LoginRateLimitController(application)

    def load_config(self):
        self.users_salt = self.application.config_parser['bzr']['salt']
        self.users_salt_2 = self.application.config_parser['bzr']['salt2']

    def init_repos(self):
        self.repo_path = os.path.join(
            self.application.db_path, 'bzr-repo')

        _logger.info('Initializing repo dir at: %s', self.repo_path)

    def init_loggerhead(self):
        self.port = random.randint(9000, 65535)
        self.loggerhead_thread = LoggerheadThread(self, self.port)

        _logger.info('Starting loggerhead server at port: %s', self.port)

        self.loggerhead_thread.start()

    def init_user_database(self):
        db_path = os.path.join(self.application.db_path, 'bzr_users.db')

        _logger.info('Initializing bzr user db at %s', db_path)

        self.bzr_users_db = sqlitejsondbm.Database(db_path)

    def norm_username(self, username):
        username = username.lower().strip('._-')

        if self.is_valid_username(username):
            return username
        else:
            raise InvalidUsernameError()

    def is_valid_username(self, username):
        return frozenset(username) <= BzrController.VALID_USERNAME_SET

    def is_valid_raw_username(self, raw_username):
        try:
            self.norm_username(raw_username)
        except InvalidUsernameError:
            return False
        else:
            return True

    def is_valid_password(self, password):
        return frozenset(password) <= BzrController.VALID_PASSWORD_SET

    def hash_password(self, username, password, timestamp):
        assert isinstance(timestamp, int)
        password_hash = hashlib.sha256(self.users_salt.encode())
        password_hash.update(username.encode())
        password_hash.update(password.encode())
        password_hash.update(str(timestamp).encode())
        return base64.b64encode(password_hash.digest()).decode()

    def check_rate_limited(self, username, remote_address):
        if username not in self.bzr_users_db:
            return False

        successful = self.application.login_rate_limit_controller \
            .record_login('bzr', username, remote_address)

        is_rate_limited = False if successful else True

        _logger.debug('Is rate limited username=%s %s', username,
            is_rate_limited)

        return is_rate_limited

    def rate_limit_whitelist(self, username, remote_address):
        if len(self.bzr_users_db) == 0:
            return

        self.application.login_rate_limit_controller \
            .whitelist_login('bzr', username, remote_address)

    def is_valid_account(self, username, password):
        if len(self.bzr_users_db) == 0:
            return True

        if not username in self.bzr_users_db:
            return False

        record_dict = self.bzr_users_db[username]
        timestamp = record_dict[DBKeys.PASSWORD_1_TIMESTAMP]
        hashed_password = self.hash_password(username, password, timestamp)

        # TODO: test for second password

        if record_dict[DBKeys.HASHED_PASSWORD_1] == hashed_password:
            return True

    def can_user_access_repo(self, username, repo_name):
        id_ = self.norm_username(username)
        # TODO: implementation


class BzrBaseRequestHandler(BaseRequestHandler):
    REALM = 'Torwuf Bzr'

    @staticmethod
    def require_auth(fn):
        @functools.wraps(fn)
        def wrapper(self, *args):
            auth_header = self.request.headers.get('authorization')

            if auth_header \
            and auth_header.startswith('Basic '):
                try:
                    plain = base64.b64decode(auth_header[6:].encode()).decode()
                except:
                    self.set_status(401)
                    self.set_header('WWW-Authenticate',
                        'Basic Realm="%s"' % BzrBaseRequestHandler.REALM)
                    self.write('Unicode characters not supported'.encode())
                    return
                else:
                    username, password = plain.split(':', 1)
                    raw_username = username

                try:
                    username = self.application.bzr.norm_username(username)
                except InvalidUsernameError:
                    username = None

                # FIXME: this occurs on every http request so not a good idea
                if username \
                and self.application.bzr.check_rate_limited(username,
                self.request.remote_ip):
                    self.set_status(403)
                    self.set_header('Content-Type', 'text/plain')
                    self.write('Too many failed login attempts in ' \
                        'the past hour'.encode())
                    return
                elif username and self.application.bzr.is_valid_account(username,
                password):
                    self.application.bzr.rate_limit_whitelist(username,
                        self.request.remote_ip)
                    self.request.username = username
                    self.request.raw_username = raw_username
                    self.request.password = password
                    fn(self, *args)
                    return

            self.set_header('WWW-Authenticate',
                'Basic Realm="%s"' % BzrBaseRequestHandler.REALM)
            self.set_status(401)
            self.render_401()

        return wrapper

    def render_401(self):
        self.set_header('Content-Type', 'text/plain')
        self.write('401 Unauthorised. \
            Please enable basic HTTP authentication.'.encode())

    @property
    def controller(self):
        return self.application.bzr


class IndexRequestHandler(BzrBaseRequestHandler):
    name = 'bzr_index'

    def get(self):
        self.render('bzr/index.html')


class ListUsersRequestHandler(BzrBaseRequestHandler):
    name = 'bzr_user_list'

    @BzrBaseRequestHandler.require_auth
    def get(self):
        users = []
        for user in self.application.bzr.bzr_users_db.keys():
            raw_username = self.application.bzr.bzr_users_db[user][DBKeys.USERNAME]
            users.append((user, raw_username))

        self.render('bzr/user_list.html', users=users)


class PasswordMixIn(object):
    def create_user(self, username, raw_username):
        id_ = self.application.bzr.norm_username(username)
        self.application.bzr.bzr_users_db[id_] = {
            DBKeys.USERNAME: raw_username,
        }

    def update_password(self, username, password):
        id_ = self.application.bzr.norm_username(username)
        timestamp = int(time.time())
        hashed_password = self.application.bzr.hash_password(username,
            password, timestamp)

        self.application.bzr.bzr_users_db.update(id_, {
            DBKeys.PASSWORD_1_TIMESTAMP: timestamp,
            DBKeys.HASHED_PASSWORD_1: hashed_password,
        })


class CreateUserRequestHandler(BzrBaseRequestHandler, PasswordMixIn):
    name = 'bzr_user_create'

    @BzrBaseRequestHandler.require_auth
    def get(self):
        self.render('bzr/user_create.html')

    @BzrBaseRequestHandler.require_auth
    def post(self):
        raw_username = self.get_argument('username')
        password = self.get_argument('password')
        confirm_password = self.get_argument('password2')

        if not self.application.bzr.is_valid_raw_username(raw_username):
            # FIXME:
#            self.add_message(
            message = (
                'Username contains unacceptable characters',
                'Please use a different username.',
            )
        else:
            username = self.controller.norm_username(raw_username)

            if password != confirm_password:
#                self.add_message(
                message = (
                    'Passwords do not match',
                    'Confirm that you’ve entered a password correctly.',
                )
            elif username in self.controller.bzr_users_db:
#                self.add_message(
                message = (
                    'User already exists',
                    'Please use a different username',
                )
            else:
                self.create_user(username, raw_username)
                self.update_password(username, password)

#                self.add_message(
                message = (
                    'Account created'
                )

        self.render('bzr/user_create.html', message=message)


class EditUserPasswordRequestHandler(BzrBaseRequestHandler, PasswordMixIn):
    name = 'bzr_user_password'

    @BzrBaseRequestHandler.require_auth
    def get(self):
        self.render('bzr/user_password.html')

    @BzrBaseRequestHandler.require_auth
    def post(self):
        password = self.get_argument('password')
        confirm_password = self.get_argument('password2')

        username = self.application.bzr.norm_username(self.request.username)

        if password != confirm_password:
            # FIXME:
#            self.add_message(
            message = (
                'Passwords do not match',
                'Confirm that you’ve entered a password correctly.',
            )
        elif username not in self.application.bzr.bzr_users_db:
#            self.add_message(
            message = (
                'The username is invalid',
                'Please check the username’s spelling',
            )
        else:
            self.update_password(username, password)

#            self.add_message(
            message = (
                'Password changed'
            )

        self.render('bzr/user_password.html', message=message)


class SignOutRequestHandler(BzrBaseRequestHandler):
    def get(self):
        self.set_header('WWW-Authenticate',
            'Basic Realm="%s"' % BzrBaseRequestHandler.REALM)
        self.redirect(self.reverse_url(IndexRequestHandler.name))


class DeleteUserRequestHandler(BzrBaseRequestHandler):
    name = 'bzr_user_delete'

    @BzrBaseRequestHandler.require_auth
    def get(self):
        self.render('bzr/user_delete.html')

    @BzrBaseRequestHandler.require_auth
    def post(self):
        raw_username = self.get_argument('username')

        if not self.application.bzr.is_valid_username(raw_username):
            # FIXME:
#            self.add_message(
            message = (
                'Username is invalid',
            )
        else:
            username = self.application.bzr.norm_username(raw_username)

            if self.request.username == username:
                _logger.info('Deleting bzr account %s', username)
                del self.application.bzr.bzr_users_db[username]

#                self.add_message(
                message = (
                    '%s deleted' % username,
                )
            else:
#                self.add_message(
                message = (
                    'Username is invalid',
                )

        self.render('bzr/user_delete.html', message=message)


class RepoRequestHandler(BzrBaseRequestHandler):
    name = 'bzr_repo'

    def check_xsrf_cookie(self):
        # Override function: intended for bzr smart server interaction
        pass

    def init(self):
        self.connection = http.client.HTTPConnection('localhost',
            self.application.bzr.port)

    def _make_connection(self, path, request_method='GET', body=None):
        http = tornado.httpclient.AsyncHTTPClient()
        path = 'http://localhost:{}/bzr/repo/{}'.format(
            self.application.bzr.port, path)
        request_headers = self._get_request_headers()

        http.fetch(HTTPRequest(path, method=request_method, body=body,
            headers=request_headers), self._on_response)

    def _get_request_headers(self):
        d = {}

        for name in self.request.headers:
            if not wsgiref.util.is_hop_by_hop(name):
                d[name] = self.request.headers[name]

        d['X-Forwarded-For'] = self.request.remote_ip
        d['X-Forwarded-Server'] = self.request.host

        return d

    def _set_response_headers(self, response):
        for name, value in response.headers.get_all():
            if not wsgiref.util.is_hop_by_hop(name):
                self.set_header(name, value)

        self.set_status(response.code)

        _logger.debug('Bzr response code %s', response.code)

    @BzrBaseRequestHandler.require_auth
    @tornado.web.asynchronous
    def get(self, *args):
        self._make_connection(args[0], 'GET')

    @BzrBaseRequestHandler.require_auth
    @tornado.web.asynchronous
    def head(self, *args):
        self._make_connection(args[0], 'HEAD')

    @BzrBaseRequestHandler.require_auth
    @tornado.web.asynchronous
    def post(self, *args):
        self._make_connection(args[0], 'POST',
            self.request.environ["wsgi.input"])

    def _on_response(self, response):
        self._set_response_headers(response)

        self.write(response.body)
        self.finish()


class RepoActionMixIn(object):
    def is_valid_repo_name(self, name):
        return name not in ('.', '..') and '/' not in name


class CreateRepoRequestHandler(BzrBaseRequestHandler, RepoActionMixIn):
    name = 'bzr_repo_create'

    @BzrBaseRequestHandler.require_auth
    def get(self):
        self.render('bzr/repo_create.html')

    @BzrBaseRequestHandler.require_auth
    def post(self):
        render_dict = {}

        message = None

        def f():
            nonlocal message
            name = self.get_argument('name')

            if not self.is_valid_repo_name(name):
                # FIXME:
#                self.add_message(
                message = (
                    'Invalid repository name'
                )
                return

            new_repo_path = os.path.join(self.application.bzr.repo_path, name)

            if os.path.exists(new_repo_path):
#                self.add_message(
                message = (
                    'Repository already exists',
                    'No action taken.',
                )

            else:
                _logger.info('Creating repository %s', new_repo_path)

                os.makedirs(new_repo_path)

                p = subprocess.Popen(['bzr', 'init-repo', new_repo_path],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                outdata, errdata = p.communicate()

                render_dict.update(
                    stdout=outdata,
                    stderr=errdata,
                    return_code=p.returncode,
                )
#                self.add_message(
                message = (
                    'Repository created',
                )

                _logger.debug('Repo creation stdout: %s', outdata)
                _logger.debug('Repo creation stderr: %s', errdata)

        f()
        render_dict['message'] = message
        self.render('bzr/repo_create.html', **render_dict)


class DeleteRepoRequestHandler(BzrBaseRequestHandler, RepoActionMixIn):
    name = 'bzr_repo_delete'

    @BzrBaseRequestHandler.require_auth
    def get(self):
        self.render('bzr/repo_delete.html')

    @BzrBaseRequestHandler.require_auth
    def post(self):
        render_dict = {}

        if not self.is_valid_repo_name(self.get_argument('name')):
            # FIXME:
#            self.add_message(
            message = (
                'Invalid repository name'
            )
        elif self.get_argument('mollyguard') == 'deletion':
            repo_path = os.path.join(self.application.bzr.repo_path,
                self.get_argument('name'))

            if not os.path.exists(repo_path):
#                self.add_message(
                message = (
                    'Repository does not exist',
                    'No action taken.'
                )
            else:
                _logger.info('Repo %s deleted', repo_path)
                shutil.rmtree(repo_path)
#                self.add_message(
                message = (
                    'Repository deleted',
                )
        else:
#            self.add_message(
            message = (
                'Incorrect guard password',
                'No action taken.'
            )

        render_dict['message'] = message

        self.render('bzr/repo_delete.html', **render_dict)


class EditUserPermissionRequestHandler(BzrBaseRequestHandler):
    name = 'bzr_user_permission'

    # TODO: implementation


url_specs = (
    URLSpec(r'/bzr/', IndexRequestHandler, name=IndexRequestHandler.name),
    URLSpec(r'/bzr/sign_out', SignOutRequestHandler),
    URLSpec(r'/bzr/repo/create', CreateRepoRequestHandler,
         name=CreateRepoRequestHandler.name),
    URLSpec(r'/bzr/repo/delete', DeleteRepoRequestHandler,
         name=DeleteRepoRequestHandler.name),
    URLSpec(r'/bzr/repo/(.*)', RepoRequestHandler,
         name=RepoRequestHandler.name),
    URLSpec(r'/bzr/user/list', ListUsersRequestHandler,
        name=ListUsersRequestHandler.name),
    URLSpec(r'/bzr/user/create', CreateUserRequestHandler,
        name=CreateUserRequestHandler.name),
    URLSpec(r'/bzr/user/password',
       EditUserPasswordRequestHandler,
       name=EditUserPasswordRequestHandler.name),
    URLSpec(r'/bzr/user/delete', DeleteUserRequestHandler,
        name=DeleteUserRequestHandler.name),
    URLSpec(r'/bzr/user/permission',
       EditUserPermissionRequestHandler,
       name=EditUserPermissionRequestHandler.name),
)
