import base64
import hashlib
import http.client
import logging
import lolram.utils.sqlitejsondbm
import lolram.web.framework.app
import os
import os.path
import string
import subprocess
import threading
import wsgiref.util

_logger = logging.getLogger(__name__)

class LoggerheadThread(threading.Thread):
	def __init__(self, controller, port):
		threading.Thread.__init__(self)
		self.isDaemon = True
		self.controller = controller
		self.port = port
		
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
			raise Exception('starting loggerhead failed')


class InvalidUsernameError(Exception):
	pass


class DBKeys(object):
	USERNAME = 'username'
	HASHED_PASSWORD_1 = 'password1'
	HASHED_PASSWORD_2 = 'password2'


class BzrController(lolram.web.framework.app.BaseController):
	VALID_USERNAME_SET = frozenset(string.ascii_lowercase) \
		| frozenset(string.digits)
	VALID_PASSWORD_SET = frozenset(string.printable)
	
	def init(self):
		self.add_url_spec(r'/bzr/', IndexRequestHandler)
		self.add_url_spec(r'/bzr/sign_out', SignOutRequestHandler)
		self.add_url_spec(r'/bzr/repo/(.*)', RepoRequestHandler)
		self.add_url_spec(r'/bzr/list_users', ListUsersRequestHandler)
		self.add_url_spec(r'/bzr/create_user', CreateUserRequestHandler)
		self.add_url_spec(r'/bzr/edit_user', EditUserRequestHandler)
		
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
		
		self.bzr_users_db = lolram.utils.sqlitejsondbm.Database(db_path)
	
	def norm_username(self, username):
		username = username.lower().strip('._-')
		
		if self.is_valid_username(username):
			return username
		else:
			raise InvalidUsernameError()
	
	def is_valid_username(self, username):
		return frozenset(username) <= BzrController.VALID_USERNAME_SET
	
	def is_valid_password(self, password):
		return frozenset(password) <= BzrController.VALID_PASSWORD_SET
	
	def hash_password(self, username, password):
		password_hash = hashlib.sha256(self.users_salt.encode())
		password_hash.update(username.encode())
		password_hash.update(password.encode())
		return base64.b64encode(password_hash.digest()).decode()
	
	def is_valid_account(self, username, password):
		hashed_password = self.hash_password(username, password)
		
		# TODO: test for second password
		
		if username in self.bzr_users_db:
			data = self.bzr_users_db[username]
			
			if data[DBKeys.HASHED_PASSWORD_1] == hashed_password:
				return True
		
		if len(self.bzr_users_db) == 0:
			return True


class BaseRequestHandler(lolram.web.framework.app.BaseHandler):
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
				
				if username \
				and self.controller.is_valid_account(username, password):
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
	@BaseRequestHandler.require_auth
	def get(self):
		users = []
		for user in self.controller.bzr_users_db.keys():
			raw_username = self.controller.bzr_users_db[user][DBKeys.USERNAME]
			users.append((user, raw_username))
			
		self.render('bzr/list_users.html', users=users)


class CreateUserRequestHandler(BaseRequestHandler):
	@BaseRequestHandler.require_auth
	def get(self):
		self.render('bzr/create_user.html')

	@BaseRequestHandler.require_auth
	def post(self):
		render_dict = {}
		
		try:
			username = self.controller.norm_username(self.get_argument('username'))
		except InvalidUsernameError:
			render_dict.update(
				layout_message_title='Username contains unacceptable characters',
				layout_message_body='Please use a different username',
			)
		else:
			password = self.get_argument('password')
			password2 = self.get_argument('password2')
			
			if username in self.controller.bzr_users_db:
				render_dict.update(
					layout_message_title='User already exists',
					layout_message_body='Please use a different username',
				)
			elif password != password2:
				render_dict.update(
					layout_message_title='Passwords do not match',
					layout_message_body='Confirm that you’ve entered a password correctly.',
				)
			elif not self.controller.is_valid_password(password):
				render_dict.update(
					layout_message_title='Passwords contains unacceptable characters',
					layout_message_body='Please use a different password.',
				)
			else:
				hashed_password = self.controller.hash_password(username,
					password)
				self.controller.bzr_users_db[username] = {
					DBKeys.HASHED_PASSWORD_1: hashed_password,
					DBKeys.USERNAME: self.get_argument('username'),
				}
				
				render_dict.update(
					layout_message_title='Account created'
				)
			
		self.render('bzr/create_user.html', **render_dict)


class EditUserRequestHandler(BaseRequestHandler):
	@BaseRequestHandler.require_auth
	def get(self):
		self.render('bzr/edit_user.html')

	@BaseRequestHandler.require_auth
	def post(self):
		render_dict = {}
		
		username = self.request.username
		password = self.get_argument('password')
		password2 = self.get_argument('password2')
		
		if password != password2:
			render_dict.update(
				layout_message_title='Passwords do not match',
				layout_message_body='Confirm that you’ve entered a password correctly.',
			)
		elif not self.controller.is_valid_password(password):
			render_dict.update(
				layout_message_title='Passwords contains unacceptable characters',
				layout_message_body='Please use a different password.',
			)
		else:
			hashed_password = self.controller.hash_password(username,
				password)
			
			self.controller.bzr_users_db.update(username, {
					DBKeys.HASHED_PASSWORD_1: hashed_password,
				})
			
			render_dict.update(
				layout_message_title='Password changed'
			)
		
		self.render('bzr/edit_user.html', **render_dict)
	

class SignOutRequestHandler(BaseRequestHandler):
	def get(self):
		self.set_header('WWW-Authenticate',
			'Basic Realm="%s"' % BaseRequestHandler.REALM)
		self.redirect(self.reverse_url(IndexRequestHandler.name))


class RepoRequestHandler(BaseRequestHandler):
	def init(self):
		self.connection = http.client.HTTPConnection('localhost',
			self.controller.port)
		
	def _make_connection(self, path, request_method='GET', body=None):
		path = '/bzr/repo/' + path 
		request_headers = self._get_request_headers()
		
		for attempt_number in range(2):
			try:
				_logger.debug('Making request to %s', path)
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
