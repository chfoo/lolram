import json
import logging
import os
import os.path
import random
import shutil
import time
import torwuf.web.controllers.base
import urllib.request

_logger = logging.getLogger(__name__)

class XKCDGeocitiesController(torwuf.web.controllers.base.BaseController):
	def init(self):
		self.add_url_spec(r'/xkcd-geocities/([0-9]*)', ComicHandler)
		self.add_url_spec(r'/xkcd-geocities/random', RandomHandler)
		self.add_url_spec(r'/xkcd[_]?geocities/([0-9a-zA-Z]*)', ComicRedirectHandler)
		self.add_url_spec(r'/xkcd-geocities/([0-9a-zA-Z]*)/', ComicRedirectHandler)
		
		self.init_data_dir()
	
	def init_data_dir(self):
		self.data_dir = os.path.join(self.config.db_path, 'xkcd_geocities')
		
		if not os.path.exists(self.data_dir):
			os.makedirs(self.data_dir)
	
	def get_current_filename(self):
		return os.path.join(self.data_dir, 'current.json')
	
	def get_latest_num(self):
		self.fetch_latest()
		
		with open(self.get_current_filename()) as f:
			data = json.load(f)
		
		return data['num']
	
	def fetch_latest(self):
		filename = self.get_current_filename()
		
		if not os.path.exists(filename) \
		or os.path.getmtime(filename) < time.time() - 86400:
			_logger.info('Fetching latest xkcd comic info')
			
			f = urllib.request.urlopen('http://xkcd.com/info.0.json')
			
			with open(filename, 'wb') as f_dest:
				shutil.copyfileobj(f, f_dest)
	
	def fetch_comic(self, num):
		filename = os.path.join(self.data_dir, '%s.json' % num)
		
		if not os.path.exists(filename):
			_logger.info('Fetching xkcd comic info = %s', num)
			
			f = urllib.request.urlopen('http://xkcd.com/%s/info.0.json' % num)
			
			with open(filename, 'wb') as f_dest:
				shutil.copyfileobj(f, f_dest)
	
	def get_comic_info(self, num):
		self.fetch_comic(num)
		
		filename = os.path.join(self.data_dir, '%s.json' % num)
		
		with open(filename) as f:
			data = json.load(f)
		
		return data

class ComicHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'xkcd_geocities'
	
	def get(self, num):
		latest_num = self.controller.get_latest_num()
		
		if num:
			num = int(num)
		else:
			num = latest_num
		
		if num > latest_num or num < 1:
			self.redirect('/xkcd-geocities/')
			return
		
		data = self.controller.get_comic_info(num)
		
		render_dict = dict(
			title=data['title'],
			image_path='/z/r/xkcd_geocities/',
			next=min(num + 1, latest_num),
			previous=max(num - 1, 1),
			first='/xkcd-geocities/1',
			last='/xkcd-geocities/%s' % latest_num,
			random='/xkcd-geocities/random',
			comic_image=data['img'],
			comic_hovertext=data['alt'],
		)
		
		self.render('xkcd_geocities/index.html', **render_dict)

class ComicRedirectHandler(torwuf.web.controllers.base.BaseHandler):
	def get(self, num):
		self.redirect('/xkcd-geocities/%s' % num, permanent=True)
		
class RandomHandler(torwuf.web.controllers.base.BaseHandler):
	def get(self):
		num = random.randint(1, self.controller.get_latest_num())
		self.redirect('/xkcd-geocities/%s' %  num)