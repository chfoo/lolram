# encoding=utf8
from lolram.components.accounts import CaptchaValidator, AccountManager
from lolram.components.accounts.dbdefs import OpenIDInfo, AccountLogsMeta
from lolram.components.database import Database
from lolram.components.session import Session
from lolram.components.wui import Document
from lolram.views import LabelURLToLinkView, BaseView
from lolram.widgets import NavigationBox, Link, Form, Table, TextBox, Button, \
	Pager, OptionGroup, Option, BaseWidget
from lxml.html import builder as lxmlbuilder
import httplib
import json
import time


#	Copyright © 2011 Christopher Foo <chris.foo@gmail.com>

#	This file is part of Lolram.

#	Lolram is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.

#	Lolram is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.

#	You should have received a copy of the GNU General Public License
#	along with Lolram.  If not, see <http://www.gnu.org/licenses/>.

__docformat__ = 'restructuredtext en'






def serve_signin(context):
	doc = Document(context)
	doc.meta.title = 'Sign in'
	
	root_password = context.request.form.getfirst('root')
	openid_url = context.request.form.getfirst('openid')
	provider = context.request.form.getfirst('provider')
	username = context.request.form.getfirst('username')
	
	captcha = CaptchaValidator(context)
	account_mgr = AccountManager(context)
	
	openid_dest_url = context.str_url(fill_controller=True,
		fill_args=True, params='openidphase2', fill_host=True)
	
	if root_password:
		if captcha.form_validate():
			account_mgr.authenticate_testing_password(root_password)
		
	elif openid_url:
		return context.response.redirect(
			account_mgr.authenticate_openid_stage_1(openid_url, openid_dest_url), 303)
		
	elif provider:
		provider_url = OpenIDInfo.providers[provider][0]
		openid_url = provider_url
		
		if provider_url.find('{{}}') != -1:
			openid_url = provider_url.replace('{{}}', username)
		
		return context.response.redirect(
			account_mgr.authenticate_openid_stage_1(openid_url, openid_dest_url), 303)
	
	elif context.request.params == 'openidphase2':
		display_name, openid_id, result_code = account_mgr.authenticate_openid_stage_2()
		db = Database(context)
		
		if openid_id:
			query = db.session.query(db.models.Account) \
				.filter_by(username=openid_id)
			
			account_model = query.first()
			
			if not account_model:
				# FIXME: this should be done in teh account manager
				account_model = db.models.Account()
				account_model.username = openid_id
				account_model.nickname = display_name
				
				for role in account_mgr.roles:
					if role.default:
						account_model.add_role(role.namespace, role.code)
				
				db.session.add(account_model)
				db.session.flush()
			
			account_mgr.apply_account_id(account_model.id) 
			
		else:
			doc.add_message('Sorry, there was a problem during the sign in process',
				'Please try again later. (Error code %s' % result_code)

	
	if account_mgr.is_authenticated():
		doc.add_message('You are now signed in')
		
		nav = NavigationBox()
		
		if account_mgr.is_authorized(AccountManager.Roles.ADMIN): 
			nav.children.append(
				Link(label='Browse users', 
					url=context.str_url(fill_controller=True, args=['list'])
				))
		
		nav.children.append(Link(label='Edit profile', 
			url=context.str_url(fill_controller=True, args=['profile'])))
		
		nav.children.append(Link(label='Sign out', 
			url=context.str_url(fill_controller=True, args=['signout'])))
		
		
		
		
		doc.append(nav)
		
	else:
	
		doc.append(SignInWidget())

def serve_account_list(context):
	db = Database(context)
	page_info = Pager(context=context)
	table = Table()
	table.header = ('ID', 'Username', 'Roles', 'Sessions', 'Profile')
	table.row_views = (LabelURLToLinkView, None, None, None, None, None)
	search_name = context.request.query.getfirst('search-name')
	query = db.session.query(db.models.Account)
	
	if search_name:
		query = query.filter(db.models.Account.username.like(u'%s%%' % search_name))
	
	query = query.limit(page_info.limit + 1).offset(page_info.offset)
	
	form = Form()
	form['search-name'] = TextBox(label='Search username')
	form['submit'] = Button(label='Search')
	
	counter = 0
	for result in query:
		url = context.str_url(fill_controller=True,
			args=('edit', str(result.id))
		)
		
		table.rows.append([
			(str(result.id), url),
			result.username,
			unicode(result.roles),
			unicode(result.sessions),
			unicode(result.profile_data),
		])
		
		counter += 1
		
		if counter >= page_info.limit:
			page_info.more = True
	
	doc = Document(context)
	doc.append(form)
	doc.append(table)
	doc.append(page_info)

def serve_account_profile(context):
	doc = Document(context)
	account_mgr = AccountManager(context)
	
	doc.meta.title = 'Profile'
	form = Form(Form.POST)
	form['nickname'] = TextBox(label='Nickname', 
		default=account_mgr.account_model.nickname)
	form['submit'] = Button(label='Save Changes')
	
	if form.validate(context):
		# FIXME:
#		nickname = form['nickname'].value
		nickname = context.request.form.getfirst('nickname')
		
		if nickname:
			account_mgr.account_model.nickname = nickname
		
			doc.add_message('Profile saved')
	
	doc.append(form)

def serve_account_edit(context):
	doc = Document(context)
	db = Database(context)
	account_mgr = AccountManager(context)
	
	account_id = context.request.args[1]
	
	account = db.session.query(db.models.Account) \
		.filter_by(id=account_id).first()
	
	if context.request.is_post:
		new_roles = set()
		
		for s in context.request.form.getlist('roles'):
			namespace, role = json.loads(s)
			new_roles.add((namespace, role))
	
		account_mgr.log_event(AccountLogsMeta.NS_ACCOUNTS,
			AccountLogsMeta.CODE_ROLE_MODIFY,
			{'ip': context.environ.get('REMOTE_ADDR'),
			'new': list(new_roles)
			},
		)
		
		account.roles = new_roles
		
		doc.add_message('Account saved', str(new_roles))
		
		return
	
	form = Form(method=Form.POST)
	opts = form['roles'] = OptionGroup(label='Roles', multi=True)
	
	for namespace, role, label, default in account_mgr.master._roles:
		active = (namespace, role) in account.roles
		key = json.dumps([namespace, role])
		
		opts[key] = Option(label=u'%s %s (%s)' % (namespace, role, label),
			default=active)
	
	form['submit'] = Button(label='Save')
	
	doc.title = u'Edit %s' % account.username
	doc.append(form)

def serve(context):
	doc = Document(context)
	account_mgr = AccountManager(context)
	
	if context.request.args:
		action = context.request.args[0]
	else:
		action = None
	
	context.response.ok()
	
	if action == 'edit':
		if account_mgr.is_authorized(AccountManager.Roles.ADMIN):
			serve_account_edit(context)
		else:
			context.response.set_status(httplib.FORBIDDEN)
		
	elif action == 'list':
		doc.meta.title = 'Listing users'
		
		if account_mgr.is_authorized(AccountManager.Roles.ADMIN):
			serve_account_list(context)
		else:
			context.response.set_status(httplib.FORBIDDEN)
		
	elif action == 'signout':
		doc.meta.title = 'Sign out'
		account_mgr.cancel_account_id()
		doc.add_message('You are now signed out')
		
	elif action == 'profile' and account_mgr.account_id:
		serve_account_profile(context)
	else:
		serve_signin(context)

def serve_captcha(context, promote_with=AccountManager.Roles.CAPTCHA_SOLVED):
	session = Session(context)
	account_mgr = AccountManager(context)
	account = account_mgr.account_model
	captcha = CaptchaValidator(context)
	
	if '_accounts_captcha_last_solved' in session.data \
	and session.data._accounts_captcha_last_solved > time.time() - 3600:
		return True
	
	doc = Document(context)
	doc.meta.title = 'Captcha'
	doc.add_message('Please complete this mathematical expression')
	
	form = Form(Form.POST)
	
	if form.validate(context) and captcha.form_validate():
		if (promote_with.namespace, promote_with.code) not in account.roles:
			account.add_role(promote_with.namespace, promote_with.code)
			account_mgr.log_event(AccountLogsMeta.NS_ACCOUNTS,
				AccountLogsMeta.CODE_ROLE_MODIFY,
				{'ip': context.environ.get('REMOTE_ADDR'),
				'reason':'captcha-self-promote',
				'role': (promote_with.namespace, promote_with.code)
				},
			)
		
		session.data._accounts_captcha_last_solved = time.time()
		
		context.response.redirect(context.request.url)
		return 
	
	
	captcha.add_form(form)
	form['submit'] = Button(label='Submit')
	doc.append(form)
	



class SignInWidget(BaseWidget):
	class default_renderer(BaseView):
		@classmethod
		def to_html(cls, context, model):
			element = lxmlbuilder.DIV(ID='accounts-sign-in-wrapper')
			
			div = lxmlbuilder.DIV(lxmlbuilder.H3('OpenID'))
			form = Form(method=Form.POST)
			form['openid'] = TextBox(label='OpenID')
			form['submit'] = Button(label='Sign in')
			
			div.append(form.render(context, 'html'))
			
			element.append(div)
			
			l = sorted(OpenIDInfo.providers.iteritems(), key=lambda i:i[0])
			
			for provider, provider_data in l:
				url, name = provider_data
				div = lxmlbuilder.DIV(lxmlbuilder.H3(name))
				
				form = Form(method=Form.POST)
				form['provider'] = TextBox(value=provider, 
					validation=TextBox.HIDDEN)
				
				if url.find('{{}}') != -1:
					form['username'] = TextBox(label=u'Username', required=True)
				
				form['submit'] = Button(label=u'Sign in')
				
				div.append(form.render(context, format='html'))
				element.append(div)
			
			captcha = CaptchaValidator(context)
			
			div = lxmlbuilder.DIV(lxmlbuilder.H3('root'))
			form = Form(method=Form.POST)
			form['root'] = TextBox(label='Password', 
				validation=TextBox.PASSWORD)
			
			captcha.add_form(form)
			
			form['submit'] =  Button(label='Sign in')
			div.append(form.render(context, format='html'))
			element.append(div)
			
			return element

def guess_provider_from_email(s):
	for provider, substrings in OpenIDInfo.emails.iteritems():
		for substring in substrings:
			if s.find(substring) != -1:
				return provider

__all__ = ['serve', 'serve_signin', 'serve_account_list', 
	'serve_account_profile', 'serve_account_edit', 'SignInWidget', 
	'guess_provider_from_email', 'serve_captcha']