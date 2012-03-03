'''Authorization decorators'''
#
#	Copyright (c) 2012 Christopher Foo <chris.foo@gmail.com>
#
#	This file is part of Torwuf.
#
#	Torwuf is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	Torwuf is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with Torwuf.  If not, see <http://www.gnu.org/licenses/>.
#
from tornado.web import HTTPError
import functools

def require_admin(fn):
	@functools.wraps(fn)
	def wrapper(self, *args, **kargs):
		if self.current_account_id \
		and self.controllers['AuthorizationController'].is_admin_account(self.current_account_uuid) \
		or self.is_testing_key_valid()\
		or self.get_current_user() == 'test:localhost':
			return fn(self, *args, **kargs)
		else:
			self.redirect('/account/login')
		
	return wrapper
	
def require_group(*group):
	def decorator_wrapper(fn):
		@functools.wraps(fn)
		def wrapper(self, *args, **kargs):
			if self.current_account_id \
			and self.controllers['AuthorizationController'].is_account_in_group(self.current_account_uuid, *group) \
			or self.is_testing_key_valid():
				return fn(self, *args, **kargs)
			elif self.current_account_id:
				raise HTTPError(403)
			else:
				self.redirect('/account/login')
		
		return wrapper
	
	return decorator_wrapper
