import logging

_logger = logging.getLogger(__name__)

class StripDummyAppPath(object):
	def __init__(self, app):
		self.app = app
	
	def __call__(self, environ, start_response):
		new_script_name = environ['SCRIPT_NAME'].replace(
			'/dummy.fcgi', '')
		new_path_info = environ['REQUEST_URI'].split('?', 1)[0]
		
		_logger.debug('SCRIPT_NAME %s to %s', environ['SCRIPT_NAME'], new_script_name)
		_logger.debug('PATH_INFO %s to ', environ['PATH_INFO'], new_path_info)
		_logger.debug('REQUEST_URI %s', environ.get('REQUEST_URI'))
		
		environ['SCRIPT_NAME'] = new_script_name
		environ['PATH_INFO'] = new_path_info
		return self.app(environ, start_response)
