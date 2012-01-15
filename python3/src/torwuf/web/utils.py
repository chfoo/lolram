
class StripDummyAppPath(object):
	def __init__(self, app):
		self.app = app
	
	def __call__(self, environ, start_response):
		environ['SCRIPT_NAME'] = environ['SCRIPT_NAME'].replace(
			'/dummy.fcgi', '')
		return self.app(environ, start_response)
