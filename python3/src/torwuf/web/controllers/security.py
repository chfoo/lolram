'''Security controllers'''
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
import time
import torwuf.web.controllers.base

# It is a bit naive and vulernable to DoS attacks
class LoginRateLimitController(torwuf.web.controllers.base.BaseController):
	KEY_TIMESTAMPS = 'timestamps'
	KEY_WHITELIST = 'whitelist'
	
	def init(self):
		self.collection = self.application.database.login_rate_limit
	
	def record_login(self, namespace, username, remote_address, limit=5):
		id_ = '%s/%s' % (namespace, username)
		result = self.collection.find_one({'_id': id_})
		past_hour = time.time() - 3600
		
		if result:
			if remote_address in result.get(LoginRateLimitController.KEY_WHITELIST, []):
				return True
			
			timestamps = result[LoginRateLimitController.KEY_TIMESTAMPS]
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