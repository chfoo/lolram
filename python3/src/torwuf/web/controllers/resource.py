from lolram.web.framework.handlers import SimpleStaticFileHandler
import glob
import logging
import os.path
import pyinotify
import shutil
import tempfile
import threading
import torwuf.web.controllers.base

_logger = logging.getLogger(__name__)


class IOEventHandler(pyinotify.ProcessEvent):
	def my_init(self, controller=None):
		self.controller = controller
		self.lock = threading.Lock()
	
	def build_resources(self):
		if self.lock.acquire(timeout=5):
			self.controller.build_resources()
			self.lock.release()
	
	def process_IN_CREATE(self, event):
		self.build_resources()
	
	def process_IN_DELETE(self, event):
		self.build_resources()
	
	def process_IN_MODIFY(self, event):
		self.build_resources()


class ResourceController(torwuf.web.controllers.base.BaseController):
	def init(self):
		image_path = os.path.join(self.application.resource_path, 'images')
		
		self.add_url_spec(r'/resource/styles.css', StylesRequestHandler)
		self.add_url_spec(r'/resource/scripts.js', ScriptsRequestHandler)
		self.add_url_spec(r'/resource/images/(.*)', SimpleStaticFileHandler, 
			path=image_path)
		self.build_resources()
		
		if self.config.debug_mode:
			self.init_ionotify()
	
	def build_resources(self):
		_logger.info('Building resources')
		self.scripts_file = tempfile.NamedTemporaryFile('wt')
		self.styles_file = tempfile.NamedTemporaryFile('wt')
		self.concatinate_scripts(self.scripts_file)
		self.concatinate_styles(self.styles_file)
	
	def init_ionotify(self):
		wm = pyinotify.WatchManager()
		mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_MODIFY
		handler = IOEventHandler(controller=self)
		notifier = pyinotify.ThreadedNotifier(wm, handler)
		
		notifier.start()
		wm.add_watch(os.path.join(self.application.resource_path, 
			'scripts'), mask, rec=True)
		wm.add_watch(os.path.join(self.application.resource_path, 
			'styles'), mask, rec=True)
	
	def concatinate_scripts(self, destination_file):
		self.concatinate_something(destination_file, 'scripts', 'js')
	
	def concatinate_styles(self, destination_file):
		self.concatinate_something(destination_file, 'styles', 'css')
	
	def concatinate_something(self, destination_file, source_type, file_extension):
		source_dir = os.path.join(self.application.resource_path, source_type)
		filenames = glob.glob('%s/*.%s' % (source_dir, file_extension)) + \
			glob.glob('%s/*/*.%s' % (source_dir, file_extension))
		
		# Open as text so byte order marks are not accidentally included 
		for filename in filenames:
			with open(filename, 'rt') as f_in:
				shutil.copyfileobj(f_in, destination_file)
			
			destination_file.write('\n')
		
		destination_file.flush()


class ScriptsRequestHandler(SimpleStaticFileHandler):
	def set_extra_headers(self, path):
		self.set_header('Content-Type', 'text/javascript')
	
	def init(self):
		self.root, self.filename = os.path.split(self.controller.scripts_file.name)
	
	def head(self):
		SimpleStaticFileHandler.head(self, self.filename)
	
	def get(self):
		SimpleStaticFileHandler.get(self, self.filename)

class StylesRequestHandler(SimpleStaticFileHandler):
	def set_extra_headers(self, path):
		self.set_header('Content-Type', 'text/css')
	
	def init(self):
		self.root, self.filename = os.path.split(self.controller.styles_file.name)
	
	def head(self):
		SimpleStaticFileHandler.head(self, self.filename)
	
	def get(self):
		SimpleStaticFileHandler.get(self, self.filename)


