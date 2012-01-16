import base64
import http.client
import logging
import lolram.web.framework.app
import os.path
import subprocess
import threading
import wsgiref.util
import os

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
			'--prefix', '/bzr/repo',
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

class BzrController(lolram.web.framework.app.BaseController):
	def init(self):
		self.add_url_spec(r'/bzr/', IndexRequestHandler)
		self.add_url_spec(r'/bzr/sign_out', SignOutRequestHandler)
		self.add_url_spec(r'/bzr/repo/(.*)', RepoRequestHandler)
#		self.add_url_spec('/bzr/create_repo', CreateRepoRequestHandler)
		
		self.init_repos()
		self.init_loggerhead()
	
	def is_valid_password(self, username, password):
		return username == 'root' and password == 'root'
	
	def init_repos(self):
		self.repo_path = os.path.join(
			self.application.config.db_path, 'bzr-repo')
		
		_logger.info('Initializing repo dir at: %s', self.repo_path)
		
	def init_loggerhead(self):
		self.port = 8093
		self.loggerhead_thread = LoggerheadThread(self, self.port)
		
		_logger.info('Starting loggerhead server at port: %s', self.port)
		
		self.loggerhead_thread.start()


class BaseRequestHandler(lolram.web.framework.app.BaseHandler):
	REALM = 'Torwuf Bzr'
	
	@staticmethod
	def require_auth(fn):
		def wrapper(self, *args):
			auth_header = self.request.headers.get('authorization')
			
			if auth_header \
			and auth_header.startswith('Basic '):
				plain = base64.b64decode(auth_header[6:].encode()).decode()
				username, password = plain.split(':', 1)
				
				if username \
				and self.controller.is_valid_password(username, password):
					self.request.username = username
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


class SignOutRequestHandler(BaseRequestHandler):
	@BaseRequestHandler.require_auth
	def get(self):
		self.set_header('WWW-Authenticate', 
			'Basic Realm="%s"' % BaseRequestHandler.REALM)
		self.set_status(401)


class RepoRequestHandler(BaseRequestHandler):
	def _make_connection(self, path, request_method='GET', body=None):
		connection = http.client.HTTPConnection('localhost', 
			self.controller.port)
		connection.request(request_method, path, body)
	
	def _set_headers(self, response):
		for header, value in response.getheaders():
			if not wsgiref.util.is_hop_by_hop(header):
				self.set_header(header, value)
		
		self.set_status(response.getcode())
		self.set_header('X-Forwarded-For', self.request.remote_ip)
		self.set_header('X-Forwarded-Server', self.request.host)
	
	@BaseRequestHandler.require_auth
	def get(self, *args):
		connection = self._make_connection(args[0], 'GET')
		response = connection.getresponse()
		
		self._set_headers(response)
		self.write(response.read())
	
	@BaseRequestHandler.require_auth
	def head(self, *args):
		connection = self._make_connection(args[0], 'HEAD')
		response = connection.getresponse()
		
		self._set_headers(response)
		self.write(response.read())
	
	@BaseRequestHandler.require_auth
	def post(self, *args):
		connection = self._make_connection(args[0], 'POST', 
			self.request.environ["wsgi.input"])
		response = connection.getresponse()
		
		self._set_headers(response)
		self.write(response.read())
