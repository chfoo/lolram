

def coroutine(func):
	'''A decorator function that takes care of starting a coroutine 
	automatically on call.
	
	:See: http://www.dabeaz.com/coroutines/
	'''
	
	def start(*args, **kwargs):
		cr = func(*args, **kwargs)
		
		cr.next()
		
		return cr
	
	return start

