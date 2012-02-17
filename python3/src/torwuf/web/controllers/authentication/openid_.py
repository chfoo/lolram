'''Openid authentication controller'''
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
from .mixins import ProcessingMixIn
from torwuf.web.models.authentication import SuccessSessionKeys
import torwuf.web.controllers.base
import urllib.parse
import xmlrpc.client

class OpenIDController(torwuf.web.controllers.base.BaseController):
	def init(self):
		# TODO: figure out how to get email
#		self.add_url_spec('/openid/show_openid', ShowOpenIDHandler)
#		self.add_url_spec('/openid/openid_stage_1', OpenIDStage1Handler)
#		self.add_url_spec('/openid/openid_stage_2', OpenIDStage2Handler)
#		self.add_url_spec('/openid/login', LoginHandler)
#		
#		self.init_server_proxy()
		pass
	
	def init_server_proxy(self):
		address = 'http://%s:%s/' % (
			self.config.config_parser['rpc2to3']['address'],
			self.config.config_parser.getint('rpc2to3', 'port')
		)
		
		self.rpc_server =  xmlrpc.client.ServerProxy(address)


class ShowOpenIDHandler(torwuf.web.controllers.base.BaseHandler):
	name = 'authen_show_openid'
	
	def get(self):
		self.render('authentication/openid/show_openid.html',
			display_id=self.get_openid_display_id(),
			identity_url=self.get_openid_identity_url(),
		)

class OpenIDBaseHandler(torwuf.web.controllers.base.BaseHandler, ProcessingMixIn):
	SESSION_KEY = 'openid_session'
	SESSION_RECENT_FAILURE_KEY = 'openid_failure'
	
	def set_openid_failure_flag(self):
		self.session[OpenIDBaseHandler.SESSION_RECENT_FAILURE_KEY] = True
	
	def get_openid_failure_flag(self):
		return self.session.get(OpenIDBaseHandler.SESSION_RECENT_FAILURE_KEY)
	
	def clear_openid_failure_flag(self):
		self.session.pop(OpenIDBaseHandler.SESSION_RECENT_FAILURE_KEY, None)
	

class LoginHandler(OpenIDBaseHandler):
	name = 'authen_login'
	
	def get(self):
		if self.get_current_user():
			self.redirect('/account/')
		
		render_dict = {
			'realm': self.get_realm()
		}
		
		if self.get_openid_failure_flag():
			render_dict['layout_message_title'] = self.locale.translate('There was a problem signing in')
			render_dict['layout_message_body'] = self.locale.translate('Please check for mistakes and try again.')
			
			self.clear_openid_failure_flag()
			self.session_commit()
		
		self.render('authentication/openid/login.html',
			**render_dict
		)

class OpenIDStage1Handler(OpenIDBaseHandler):
	name = 'authen_openid_stage_1'
	
	def post(self):
		realm = self.get_realm()
		openid_url = self.get_argument('openid')
		return_to_url = self.request.protocol + "://" + self.request.host + \
			self.reverse_url(OpenIDStage2Handler.name)
		result = self.controller.rpc_server.openid_stage_1(openid_url, 
			return_to_url, realm)
		
		if result:
			redirect_url, session_data = result
			self.session[OpenIDBaseHandler.SESSION_KEY] = session_data
			self.session_commit()
			self.redirect(redirect_url)
		else:
			self.set_openid_failure_flag()
			self.session_commit()
			self.redirect(return_to_url)


class OpenIDStage2Handler(OpenIDBaseHandler):
	name = 'authen_openid_stage_2'
	destination_table = {
		'show_openid': ShowOpenIDHandler.name
	}
	
	def get(self):
		query_kvp_dict = dict(urllib.parse.parse_qsl(self.request.query))
		session_data = self.session.get(OpenIDBaseHandler.SESSION_KEY, '')
		
		result = self.controller.rpc_server.openid_stage_2(session_data, 
			query_kvp_dict, self.request.full_url())
		
		if result:
			identity_url, display_id = result
			self.session[SuccessSessionKeys.KEY] = {
				SuccessSessionKeys.OPENID : identity_url,
				SuccessSessionKeys.DISPLAY_NAME : display_id,
			}
			
			self.session.pop(OpenIDBaseHandler.SESSION_KEY, None)
			self.session_commit()
			self.redirect(self.reverse_url('account_openid_success'))
		else:
			self.set_openid_failure_flag()
			self.session_commit()
			self.redirect(self.reverse_url(LoginHandler.name))
