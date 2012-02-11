import http.client
import traceback
import logging
_logger = logging.getLogger(__name__)

class ErrorOutputHandlerMixin(object):
	def write_error(self, status_code, exc_info=None, **kwargs):
		status_msg = http.client.responses.get(status_code, '')
		template_name = 'error/server_error.html'
		
		if status_code == 404:
			template_name = 'error/not_found_error.html'
		
		elif 400 <= status_code < 500:
			template_name = 'error/client_error.html'
			
		if exc_info:
			try:
				traceback_str = '\n'.join(traceback.format_exception(*exc_info))
			except:
				_logger.exception('Exception during formatting exception')
				traceback_str = '(Error during formatting exception)'
		else:
			traceback_str = ''
		
		self.render(template_name, status_code=status_code, 
			status_msg=status_msg, traceback_str=traceback_str)
		