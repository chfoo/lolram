import lolram.web.framework.app
import time

# It is a bit naive and vulernable to DoS attacks
class LoginRateLimitController(lolram.web.framework.app.BaseController):
	KEY_TIMESTAMPS = 'timestamps'
	
	def init(self):
		self.collection = self.application.database.login_rate_limit
	
	def record_login(self, username, namespace='', limit=5):
		id_ = '%s/%s' % (namespace, username)
		result = self.collection.find_one({'_id': id_})
		past_hour = time.time() - 3600
		
		if result:
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
