'''Simple BZR repositories over HTTP controllers'''
#
#    Copyright (c) 2012 Christopher Foo <chris.foo@gmail.com>
#
#    This file is part of Torwuf.
#
#    Torwuf is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Torwuf is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Torwuf.  If not, see <http://www.gnu.org/licenses/>.
#
import base64
import hashlib
import http.client
import logging
import lolram.sqlitejsondbm
import os.path
import shutil
import string
import subprocess
import threading
import time
import torwuf.web.controllers.base
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
        self.log_dir = os.path.join(self.controller.config.root_path, 'logs',
            'bzr')

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


class InvalidUsernameError(Exception):
    pass


class DBKeys(object):
    USERNAME = 'username'
    HASHED_PASSWORD_1 = 'password1'
    HASHED_PASSWORD_2 = 'password2'
    PASSWORD_1_TIMESTAMP = 'pwTimestamp1'
    REPO_READWRITE_LIST = 'repoRWList'


class BzrController(torwuf.web.controllers.base.BaseController):
    VALID_USERNAME_SET = frozenset(string.ascii_lowercase) \
        | frozenset(string.digits)
    VALID_PASSWORD_SET = frozenset(string.printable)

    def init(self):
        self.add_url_spec(r'/bzr/', IndexRequestHandler)
        self.add_url_spec(r'/bzr/sign_out', SignOutRequestHandler)
        self.add_url_spec(r'/bzr/repo/create', CreateRepoRequestHandler)
        self.add_url_spec(r'/bzr/repo/delete', DeleteRepoRequestHandler)
        self.add_url_spec(r'/bzr/repo/(.*)', RepoRequestHandler)
        self.add_url_spec(r'/bzr/user/list', ListUsersRequestHandler)
        self.add_url_spec(r'/bzr/user/create', CreateUserRequestHandler)
        self.add_url_spec(r'/bzr/user/password',
            EditUserPasswordRequestHandler)
        self.add_url_spec(r'/bzr/user/delete', DeleteUserRequestHandler)
        self.add_url_spec(r'/bzr/user/permission',
            EditUserPermissionRequestHandler)

        self.load_config()
        self.init_repos()
        self.init_loggerhead()
        self.init_user_database()

    def load_config(self):
        self.users_salt = self.config.config_parser['bzr']['salt']
        self.users_salt_2 = self.config.config_parser['bzr']['salt2']

    def init_repos(self):
        self.repo_path = os.path.join(
            self.application.config.db_path, 'bzr-repo')

        _logger.info('Initializing repo dir at: %s', self.repo_path)

    def init_loggerhead(self):
        self.port = 8093
        self.loggerhead_thread = LoggerheadThread(self, self.port)

        _logger.info('Starting loggerhead server at port: %s', self.port)

        self.loggerhead_thread.start()

    def init_user_database(self):
        db_path = os.path.join(self.config.db_path, 'bzr_users.db')

        _logger.info('Initializing bzr user db at %s', db_path)

        self.bzr_users_db = lolram.sqlitejsondbm.Database(db_path,
            check_same_thread=False)

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
        password_hash = hashlib.sha256(self.users_salt.encode())
        password_hash.update(username.encode())
        password_hash.update(password.encode())
        password_hash.update(str(timestamp).encode())
        return base64.b64encode(password_hash.digest()).decode()

    def check_rate_limited(self, username, remote_address):
        if username not in self.bzr_users_db:
            return False

        successful = self.application.controllers['LoginRateLimitController'] \
            .record_login('bzr', username, remote_address)

        is_rate_limited = False if successful else True

        _logger.debug('Is rate limited username=%s %s', username,
            is_rate_limited)

        return is_rate_limited

    def rate_limit_whitelist(self, username, remote_address):
        if len(self.bzr_users_db) == 0:
            return

        self.application.controllers['LoginRateLimitController'] \
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


class BaseRequestHandler(torwuf.web.controllers.base.BaseHandler):
    REALM = 'Torwuf Bzr'

    @staticmethod
    def require_auth(fn):
        def wrapper(self, *args):
            auth_header = self.request.headers.get('authorization')

            if auth_header \
            and auth_header.startswith('Basic '):
                try:
                    plain = base64.b64decode(auth_header[6:].encode()).decode()
                except:
                    self.set_status(401)
                    self.set_header('WWW-Authenticate',
                        'Basic Realm="%s"' % BaseRequestHandler.REALM)
                    self.write('Unicode characters not supported'.encode())
                    return
                else:
                    username, password = plain.split(':', 1)
                    raw_username = username

                try:
                    username = self.controller.norm_username(username)
                except InvalidUsernameError:
                    username = None

                # FIXME: this occurs on every http request so not a good idea
                if username \
                and self.controller.check_rate_limited(username,
                self.request.remote_ip):
                    self.set_status(403)
                    self.set_header('Content-Type', 'text/plain')
                    self.write('Too many failed login attempts in ' \
                        'the past hour'.encode())
                    return
                elif username and self.controller.is_valid_account(username,
                password):
                    self.controller.rate_limit_whitelist(username,
                        self.request.remote_ip)
                    self.request.username = username
                    self.request.raw_username = raw_username
                    self.request.password = password
                    fn(self, *args)
                    return

            self.set_header('WWW-Authenticate',
                'Basic Realm="%s"' % BaseRequestHandler.REALM)
            self.set_status(401)
            self.render_401()

        return wrapper

    def render_401(self):
        self.set_header('Content-Type', 'text/plain')
        self.write('401 Unauthorised. \
            Please enable basic HTTP authentication.'.encode())


class IndexRequestHandler(BaseRequestHandler):
    name = 'bzr_index'

    def get(self):
        self.render('bzr/index.html')


class ListUsersRequestHandler(BaseRequestHandler):
    name = 'bzr_user_list'

    @BaseRequestHandler.require_auth
    def get(self):
        users = []
        for user in self.controller.bzr_users_db.keys():
            raw_username = self.controller.bzr_users_db[user][DBKeys.USERNAME]
            users.append((user, raw_username))

        self.render('bzr/user_list.html', users=users)


class PasswordMixIn(object):
    def create_user(self, username, raw_username):
        id_ = self.controller.norm_username(username)
        self.controller.bzr_users_db[id_] = {
            DBKeys.USERNAME: raw_username,
        }

    def update_password(self, username, password):
        id_ = self.controller.norm_username(username)
        timestamp = int(time.time())
        hashed_password = self.controller.hash_password(username, password,
            timestamp)

        self.controller.bzr_users_db.update(id_, {
            DBKeys.PASSWORD_1_TIMESTAMP: timestamp,
            DBKeys.HASHED_PASSWORD_1: hashed_password,
        })


class CreateUserRequestHandler(BaseRequestHandler, PasswordMixIn):
    name = 'bzr_user_create'

    @BaseRequestHandler.require_auth
    def get(self):
        self.render('bzr/user_create.html')

    @BaseRequestHandler.require_auth
    def post(self):
        raw_username = self.get_argument('username')
        password = self.get_argument('password')
        confirm_password = self.get_argument('password2')

        if not self.controller.is_valid_raw_username(raw_username):
            self.add_message(
                'Username contains unacceptable characters',
                'Please use a different username.',
            )
        else:
            username = self.controller.norm_username(raw_username)

            if password != confirm_password:
                self.add_message(
                    'Passwords do not match',
                    'Confirm that you’ve entered a password correctly.',
                )
            elif username in self.controller.bzr_users_db:
                self.add_message(
                    'User already exists',
                    'Please use a different username',
                )
            else:
                self.create_user(username, raw_username)
                self.update_password(username, password)

                self.add_message(
                    'Account created'
                )

        self.render('bzr/user_create.html')


class EditUserPasswordRequestHandler(BaseRequestHandler, PasswordMixIn):
    name = 'bzr_user_password'

    @BaseRequestHandler.require_auth
    def get(self):
        self.render('bzr/user_password.html')

    @BaseRequestHandler.require_auth
    def post(self):
        password = self.get_argument('password')
        confirm_password = self.get_argument('password2')

        username = self.controller.norm_username(self.request.username)

        if password != confirm_password:
            self.add_message(
                'Passwords do not match',
                'Confirm that you’ve entered a password correctly.',
            )
        elif username not in self.controller.bzr_users_db:
            self.add_message(
                'The username is invalid',
                'Please check the username’s spelling',
            )
        else:
            self.update_password(username, password)

            self.add_message(
                'Password changed'
            )

        self.render('bzr/user_password.html',)


class SignOutRequestHandler(BaseRequestHandler):
    def get(self):
        self.set_header('WWW-Authenticate',
            'Basic Realm="%s"' % BaseRequestHandler.REALM)
        self.redirect(self.reverse_url(IndexRequestHandler.name))


class DeleteUserRequestHandler(BaseRequestHandler):
    name = 'bzr_user_delete'

    @BaseRequestHandler.require_auth
    def get(self):
        self.render('bzr/user_delete.html')

    @BaseRequestHandler.require_auth
    def post(self):
        raw_username = self.get_argument('username')

        if not self.controller.is_valid_username(raw_username):
            self.add_message(
                'Username is invalid',
            )
        else:
            username = self.controller.norm_username(raw_username)

            if self.request.username == username:
                _logger.info('Deleting bzr account %s', username)
                del self.controller.bzr_users_db[username]

                self.add_message(
                    '%s deleted' % username,
                )
            else:
                self.add_message(
                    'Username is invalid',
                )

        self.render('bzr/user_delete.html')


class RepoRequestHandler(BaseRequestHandler):
    name = 'bzr_repo'

    def check_xsrf_cookie(self):
        # Override function: intended for bzr smart server interaction
        pass

    def init(self):
        self.connection = http.client.HTTPConnection('localhost',
            self.controller.port)

    def _make_connection(self, path, request_method='GET', body=None):
        path = '/bzr/repo/' + path
        request_headers = self._get_request_headers()

        for attempt_number in range(2):
            try:
                _logger.debug('Making request to request_method=%s, path=%s, headers=%s', request_method, path, request_headers)
                self.connection.request(request_method, path, body, headers=request_headers)

                break
            except http.client.NotConnected:
                _logger.debug('Not Connected')
                self.connection.connect()

        return self.connection

    def _get_request_headers(self):
        d = {}

        for name in self.request.headers:
            if not wsgiref.util.is_hop_by_hop(name):
                d[name] = self.request.headers[name]

        d['X-Forwarded-For'] = self.request.remote_ip
        d['X-Forwarded-Server'] = self.request.host

        return d

    def _set_response_headers(self, response):
        for name, value in response.getheaders():
            if not wsgiref.util.is_hop_by_hop(name):
                self.set_header(name, value)

        self.set_status(response.getcode())

        _logger.debug('Bzr response code %s', response.getcode())

    @BaseRequestHandler.require_auth
    def get(self, *args):
        connection = self._make_connection(args[0], 'GET')
        response = connection.getresponse()

        self._set_response_headers(response)
        self.write(response.read())

    @BaseRequestHandler.require_auth
    def head(self, *args):
        connection = self._make_connection(args[0], 'HEAD')
        response = connection.getresponse()

        self._set_response_headers(response)
        self.write(response.read())

    @BaseRequestHandler.require_auth
    def post(self, *args):
        connection = self._make_connection(args[0], 'POST',
            self.request.environ["wsgi.input"])
        response = connection.getresponse()

        self._set_response_headers(response)
        self.write(response.read())


class RepoActionMixIn(object):
    def is_valid_repo_name(self, name):
        return name not in ('.', '..') and '/' not in name


class CreateRepoRequestHandler(BaseRequestHandler, RepoActionMixIn):
    name = 'bzr_repo_create'

    @BaseRequestHandler.require_auth
    def get(self):
        self.render('bzr/repo_create.html')

    @BaseRequestHandler.require_auth
    def post(self):
        render_dict = {}

        def f():
            name = self.get_argument('name')

            if not self.is_valid_repo_name(name):
                self.add_message(
                    'Invalid repository name'
                )
                return

            new_repo_path = os.path.join(self.controller.repo_path, name)

            if os.path.exists(new_repo_path):
                self.add_message(
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
                self.add_message(
                    'Repository created',
                )

                _logger.debug('Repo creation stdout: %s', outdata)
                _logger.debug('Repo creation stderr: %s', errdata)

        f()
        self.render('bzr/repo_create.html', **render_dict)


class DeleteRepoRequestHandler(BaseRequestHandler, RepoActionMixIn):
    name = 'bzr_repo_delete'

    @BaseRequestHandler.require_auth
    def get(self):
        self.render('bzr/repo_delete.html')

    @BaseRequestHandler.require_auth
    def post(self):
        render_dict = {}

        if not self.is_valid_repo_name(self.get_argument('name')):
            self.add_message(
                'Invalid repository name'
            )
        elif self.get_argument('mollyguard') == 'deletion':
            repo_path = os.path.join(self.controller.repo_path,
                self.get_argument('name'))

            if not os.path.exists(repo_path):
                self.add_message(
                    'Repository does not exist',
                    'No action taken.'
                )
            else:
                _logger.info('Repo %s deleted', repo_path)
                shutil.rmtree(repo_path)
                self.add_message(
                    'Repository deleted',
                )
        else:
            self.add_message(
                'Incorrect guard password',
                'No action taken.'
            )

        self.render('bzr/repo_delete.html', **render_dict)


class EditUserPermissionRequestHandler(BaseRequestHandler):
    name = 'bzr_user_permission'

    # TODO: implementation
