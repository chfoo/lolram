# encoding=utf8

'''Content management system'''

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

import os.path
import uuid
import mimetypes

import lxml.html.builder as lxmlbuilder
import lxml.html

from lolram import util
from lolram.components.accounts import AccountManager, CaptchaValidator
from lolram.components.cms import CMS
from lolram.components.cms.dbdefs import ArticleActions, ArticleViewModes, \
	ArticleMetadataFields
from lolram.components.lion import Lion
from lolram.dataobject import MVPair
from lolram.views import LabelURLToLinkView, BaseView
from lolram.widgets import NavigationBox, Link, Document, Table, Pager, Form, \
	TextBox, OptionGroup, Option, Button, HorizontalBox, Text, VerticalBox
import lolram.components.accounts.serve

GET = 'g'
GET_VERSION = 'v'
BROWSE = 'b'
ALL = 'a'
ARTICLES = 't'
FILES = 'f'
HISTORY = 'h'
NEW = 'n'
EDIT = 'e'
UPLOAD = 'u'
RAW = 'r'
EDIT_VIEW = 'd'
TEXVC = 'x'
CAPTCHA = 'c'

SESSION_CAPTCHA_KEY = '_cms_captcha'
	

def serve(context):
	cms = CMS(context)
	doc = Document(context)
	arg1 = None
	action = context.request.params
	account_mgr = AccountManager(context)
	
	if len(context.request.args) == 1:
		arg1 = context.request.args[0]
	elif len(context.request.args) > 1:
		action = None
	
	if arg1 and not action:
		article = None
		uuid_bytes = None
		
		try:
			uuid_bytes = util.b32low_to_bytes(arg1)
		except TypeError:
			pass
		
		if uuid_bytes:
			article = cms.get_article(uuid=uuid_bytes)
		
		if not article:
			article = cms.get_article(address=arg1)
		
		if article:
			if _check_permissions(context, ArticleActions.VIEW_TEXT, article.current):
				context.response.set_status(403)
				return
			
			article.current._allow_intern = True
			context.response.ok()
			
			item_limit = 50
			if article.current.view_mode & ArticleViewModes.CATEGORY:
				nested_count = -1
				item_limit = 0
			else:
				nested_count = 5
			
			
			_build_article_page(context, article.current, nested_count, item_limit)
			
			if article.current.view_mode & ArticleViewModes.CATEGORY:
				_build_single_article_listing(context, article)
			
			if article.primary_address:
				context.response.headers.add('Link', 
					u'<%s>' % context.str_url(fill_controller=True,
						args=[article.primary_address]), rel='Canonical')
			
	
	elif action == GET_VERSION and arg1:
		uuid_bytes = util.b32low_to_bytes(arg1)
		article = cms.get_article_history(uuid=uuid_bytes)
		
		if article:
			if _check_permissions(context, ArticleActions.VIEW_HISTORY, article):
				context.response.set_status(403)
				return
			
			context.response.ok()
			_build_article_version(context, article)
			
			if article.article.primary_address:
				context.response.headers.add('Link', 
					u'<%s>' % context.str_url(fill_controller=True,
						args=[article.article.primary_address]), rel='Canonical')
			
			article._allow_intern = True
	
	elif action and action[0] == BROWSE:
		context.response.ok()
		
		if action[1] == ARTICLES:
			_build_article_listing(context, True, False)
		elif action[1] == FILES:
			_build_article_listing(context, False, True)
		else:
			_build_article_listing(context)
	
	elif action == HISTORY and arg1:
		uuid_bytes = util.b32low_to_bytes(arg1)
		article = cms.get_article(uuid=uuid_bytes)
		
		if article:
			context.response.ok()
			_build_article_history_listing(context, article)
	
	elif action and action[0] in (EDIT, UPLOAD):
		edit_type = FILES
			
		if len(action) == 2 and action[1] == UPLOAD:
			edit_type = UPLOAD
		
		if arg1:
			uuid_bytes = util.b32low_to_bytes(arg1)
			article = cms.get_article(uuid=uuid_bytes)
			article_version = article.edit()
			
			if _check_permissions(context, ArticleActions.EDIT_TEXT, article_version):
				context.response.set_status(403)
				return
		else:
			article = cms.new_article()
			article_version = article.edit()
			
		context.response.ok()
		
		if account_mgr.is_authorized(AccountManager.Roles.SUPERUSER):
			article_version._allow_intern = True
		
		if action[0] == EDIT:
			if (article_version.text or 'text' in context.request.form)\
			and not 'submit-publish' in context.request.form:
				# FIXME: due to dependencies, text must be set for previewer
				article_version.text = context.request.form.getfirst('text', article_version.text)
				_build_article_preview(context, article_version)
			
			_build_edit_page(context, article_version)
		else:
			_build_edit_page(context, article_version, upload=True)
	
	elif action == RAW and arg1:
		uuid_bytes = util.b32low_to_bytes(arg1)
		article = cms.get_article_history(uuid=uuid_bytes)
		
		if article:
			if _check_permissions(context, ArticleActions.VIEW_TEXT, article):
				context.response.set_status(403)
				return
			
			context.response.ok()
			
			if article.article.primary_address:
				context.response.headers.add('Link', 
					u'<%s>' % context.str_url(fill_controller=True,
						args=[article.article.primary_address]), 
							rel='Canonical')
			
			return _serve_raw(context, article)
	
	elif action == EDIT_VIEW and arg1:
		uuid_bytes = util.b32low_to_bytes(arg1)
		article = cms.get_article(uuid=uuid_bytes)
		article_version = article.edit()
		
		if _check_permissions(context, ArticleActions.EDIT_TEXT_PROPERTIES, article_version):
			context.response.set_status(403)
			return
		
		context.response.ok()
		_build_article_edit_view_page(context, article_version)
	
	elif action == TEXVC and arg1:
		dest_dir = os.path.join(context.dirinfo.var, 'texvc', arg1[0:2])
		dest_path = os.path.join(dest_dir, '%s.png' % arg1)
	
		context.response.ok()
		return context.response.output_file(dest_path)
	
	else:
		context.response.set_status(404)
	
	
	nav = NavigationBox()
	nav.children.append(
		Link('Browse', context.str_url(fill_controller=True,
			args=[''],
			params=BROWSE+'a')
		)
	)
	
	if account_mgr.is_authorized(AccountManager.Roles.USER):
		nav.children.append(
			Link('New article', context.str_url(fill_controller=True,
			args=[''],
			params=EDIT+NEW)))
		nav.children.append(Link(
			'Upload', context.str_url(fill_controller=True,
			args=[''],
			params=UPLOAD+NEW)))
	
	doc.append(nav)
	
def _build_article_page(context, article, nested_count=5, item_limit=20):
	doc = Document(context)
	doc.title = article.title or article.upload_filename
	pager = Pager(context=context)
	
	if article.doc_info:
		doc.title = article.doc_info.title
		doc.meta.subtitle = article.doc_info.subtitle
		
		for k, v in article.doc_info.meta.iteritems():
			if v is not None:
				doc.meta[k] = v
	
	offset = pager.offset
	doc.append(pager)
	doc.append(MVPair(article, ArticleLinearView, offset=offset, limit=item_limit))
	doc.append(pager)

def _build_article_version(context, article_history):
	doc = Document(context)
	
	doc.title = u'Viewing past version %s: %s' % \
		(article_history.version, 
		article_history.title or article_history.upload_filename)
	doc.append(MVPair(article_history, ArticleSingleDetailView))

def _build_article_preview(context, article_history):
	doc = Document(context)
	doc_info = article_history.doc_info
	
	if article_history.title:
		doc.title = u'Editing %s' % article_history.title
	
	doc.add_message(u'This is only a preview', 'Your changes have not been saved!')
	
	if doc_info and doc_info.errors:
		doc.add_message(u'There are syntax errors in the document',
			doc_info.errors)
	
	doc.append(MVPair(article_history, ArticlePreviewView))

def _build_article_listing(context, show_articles=True, show_files=True):
	doc = Document(context)
	cms = CMS(context)
	lion = Lion(context)
	
	page_info = context.page_info(limit=50)
	articles = cms.get_articles(page_info.offset, page_info.limit + 1,
		date_sort_desc=True)
	
	table = Table()
	table.headers = ('Title', 'Date')
	
	counter = 0
	for article in articles:
		if counter < page_info.limit:
			table.rows.append((
				(article.title or article.current.upload_filename or '(untitled)', 
					context.str_url(fill_controller=True,
					args=[util.bytes_to_b32low(article.uuid.bytes)],
					)), 
				lion.formatter.datetime(article.publish_date), 
			))
		else:
			page_info.more = True
		
		counter += 1
	
	if counter:
		doc.append(Pager(page_info))
		doc.append(MVPair(table, 
			row_views=(LabelURLToLinkView, None)))
		doc.append(Pager(page_info))

def _build_single_article_listing(context, article):
	doc = Document(context)
	cms = CMS(context)
	lion = Lion(context)
	page_info = context.page_info(limit=50)
	sort_method = context.request.query.getfirst('s', 'title')
	sort_desc = context.request.query.getfirst('o')
	children = article.get_children(page_info.offset, page_info.limit + 1,
		sort_method=sort_method, sort_desc=sort_desc,
	)
	
	table = Table()
	table.headers = ('Title', 'Date')
	
	counter = 0
	for article in children:
		if counter < page_info.limit:
			table.rows.append((
				(article.title or article.current.upload_filename or '(untitled)', 
					context.str_url(fill_controller=True,
					args=[article.primary_address or util.bytes_to_b32low(article.uuid.bytes)],
					)), 
				lion.formatter.datetime(article.publish_date), 
			))
		else:
			page_info.more = True
		
		counter += 1
	
	if counter:
		doc.append(MVPair(table, 
			row_views=(LabelURLToLinkView, None)))
		doc.append(Pager(page_info))

def _build_article_history_listing(context, article):
	doc = Document(context)
	cms = CMS(context)
	lion = Lion(context)
	
	page_info = context.page_info(limit=50)
		
	table = Table()
	table.header = ('Version', 'Date', 'Title')
			
	counter = 0
	for info in article.get_history(page_info.offset, page_info.limit):
		url = context.str_url(fill_controller=True,
			args=[CMS.model_uuid_str(info)], params=GET_VERSION,)
		
		table.rows.append((
			str(info.version), 
			lion.formatter.datetime(info.date), 
			(info.title or info.upload_filename or '(untitled)', url),
		))
				
		counter += 1
		if counter > 50:
			page_info.more = True
			break
	
	doc.append(Pager(page_info))
	doc.append(MVPair(table, 
		row_views=(None, None, LabelURLToLinkView)))
	doc.append(Pager(page_info))

def _serve_raw(context, article_history):
	context.response.headers['last-modified'] = str(article_history.date)
			
	if article_history.text:
		context.response.set_content_type('text/plain')
		return [article_history.text.encode('utf8')]
	else:
		return context.response.output_file(
			article_history.file.filename,
			download_filename=article_history.upload_filename)

def _build_edit_page(context, article_version, upload=False):
	if not lolram.components.accounts.serve.serve_captcha(context):
		return
	
	doc = Document(context)
	cms = CMS(context)
	account_mgr = AccountManager(context) 

	wiki_article_mode = article_version.view_mode & ArticleViewModes.EDITABLE_BY_OTHERS \
		and account_mgr.is_authorized(AccountManager.Roles.USER)
		
		
	form = Form(Form.POST, 
		context.str_url(fill_path=True, 
			fill_args=True, fill_params=True, fill_query=True))
	
	if wiki_article_mode and _check_permissions(context, ArticleActions.EDIT_TEXT, article_version) \
	or _check_permissions(context, ArticleActions.COMMENT_ON_TEXT, article_version):
		context.response.set_status(403)
		doc.add_message('You do not have permission to edit this page')
		return
	
	if form.validate(context) and 'submit-preview' not in context.request.form:
		article_version.reason = context.request.form.getfirst('reason')
		address = context.request.form.getfirst('address')
		
		if wiki_article_mode and not article_version.addresses and address:
			article_version.addresses = article_version.addresses | \
				frozenset([address])
		
		parent_str = context.request.form.getfirst('parent')
		
		if parent_str:
			uuid_bytes = util.b32low_to_bytes(parent_str)
			parent_article = cms.get_article(uuid=uuid_bytes)
			
			if wiki_article_mode or parent_article.current.view_mode | ArticleViewModes.ALLOW_COMMENTS:
				article_version.parents |= frozenset([parent_article])
		
		if upload:
			article_version.upload_filename = context.request.form['file'].filename
			article_version.file = context.request.form['file'].file
		
			if context.request.form.getfirst('use-filename'):
				address = context.request.form['file'].filename
				article_version.view_mode = article_version.view_mode | ArticleViewModes.FILE
		
		else:
			article_version.text = context.request.form.getfirst('text')
			doc_info = article_version.doc_info
			date = doc_info.meta.get('date')
			
			if date:
				article_version.publish_date = date
				article_version.metadata[ArticleMetadataFields.TITLE] = (doc_info.title or article_version.text)[:160]
		
		if wiki_article_mode:
			if not article_version.addresses and address:
				article_version.addresses = article_version.addresses | \
					frozenset([address])
			
		elif account_mgr.is_authorized(AccountManager.Roles.USER) \
		and 'is-article' in context.request.form:
			article_version.view_mode = article_version.view_mode | ArticleViewModes.EDITABLE_BY_OTHERS
		
		article_version.save()
		doc.add_message('Edit was a success')
		
		return
	
	if not article_version.addresses and wiki_article_mode:
		form['address'] = TextBox(label='Address (optional):')
		
		if upload:
			opts = OptionGroup(label='Use upload filename as address')
			opts['yes'] = Option(label='Yes', active=True)
			form['use-filename'] = opts
		
	if upload:
		form['file'] = TextBox(label='File:', validation=TextBox.FILE, required=True)
	
	else:
		# XXX must be pure unicode otherwise lxml complains
		s = context.request.form.getfirst('text')
		text = unicode(s or article_version.text or '')
	
	if not article_version.addresses \
	and wiki_article_mode:
		form['address'] = TextBox(label='Address (optional):')
	
	if not upload:
		form['text'] = TextBox(label='Article content:', default=text, large=True, required=True)
	
	if article_version.version != 1 or wiki_article_mode:
		form['reason'] = TextBox(label='Reason or changes (optional):')

	if upload:
		form['submit-publish'] = Button(label='Upload')
	else:
		form['submit-publish'] = Button(label='Publish')
		form['submit-preview'] = Button(label='Preview')
	
	doc.append(form)
	

def _build_article_edit_view_page(context, article_history):
	cms = CMS(context)
	doc = Document(context)
	
	if article_history.view_mode is None:
		article_history.view_mode = 0
	
	form = Form(Form.POST, 
		context.str_url(fill_path=True, 
			fill_args=True, fill_params=True, fill_query=True))
	
	if form.validate(context):
		address = context.request.form.getfirst('address')
		addresses = context.request.form.getfirst('addresses')
		addresses = filter(None, addresses.splitlines())
		parents = context.request.form.getfirst('parents')
		parents = filter(None, parents.splitlines())
		
		article_history.addresses = frozenset(addresses)
		if address:
			article_history.primary_address = address
		
		parent_list = []
		for uuid_hex in parents:
			parent = cms.get_article(uuid=uuid.UUID(uuid_hex).bytes)
			parent_list.append(parent)
		
		article_history.parents = frozenset(parent_list)
		
		view_modes = context.request.form.getlist('view-modes')
		article_history.view_mode = 0
		
		# FIXME: better table lookup
		d = {
			'file': ArticleViewModes.FILE,
			'editable-by-others': ArticleViewModes.EDITABLE_BY_OTHERS,
			'category': ArticleViewModes.CATEGORY,
			'viewable': ArticleViewModes.VIEWABLE,
			'comments': ArticleViewModes.ALLOW_COMMENTS,
		}
		
		for mode in view_modes:
			v = d[mode]
			article_history.view_mode = article_history.view_mode | v
		
		article_history.reason = context.request.form.getfirst('reason')
		article_history.save()
		
		doc.add_message('Changes have been saved')
		
		return
	
	
	form['address'] = TextBox(label='Prefered address', 
		default=article_history.article.primary_address)
	form['addresses'] = TextBox(label='Addresses', 
		default=u'\n'.join(article_history.addresses), large=True)
	form['parents'] = TextBox(label='Parents', 
		default=u'\n'.join([a.uuid.urn for a in article_history.parents]), 
		large=True)
	
	opts = OptionGroup(label='View Modes', multi=True)
	opts['file'] = Option(label='File', 
		default=article_history.view_mode & ArticleViewModes.FILE)
	opts['editable-by-others'] = Option(label='Editable by others (Wiki article)', 
		default=article_history.view_mode & ArticleViewModes.EDITABLE_BY_OTHERS)
	opts['category'] = Option(label='Is a category', 
		default=article_history.view_mode & ArticleViewModes.CATEGORY)
	opts['viewable'] = Option(label='Viewable', 
		default=article_history.view_mode & ArticleViewModes.VIEWABLE)
	opts['comments'] = Option(label='Allow comments', 
		default=article_history.view_mode & ArticleViewModes.ALLOW_COMMENTS)
	
	form['view-modes'] = opts
	
	form['reason'] = TextBox(label='Reason for edit (optional)')
	form['submit'] =  Button(label='Save')
	
	doc.append(form)

def _check_permissions(context, action, article_history):
	account_mgr = AccountManager(context)
	doc = Document(context)
	
	if action == ArticleActions.VIEW_TEXT \
	and not article_history.view_mode & ArticleViewModes.VIEWABLE:
		doc.add_message('Sorry, you may not view this article')
		return True
	
	if action == ArticleActions.VIEW_HISTORY \
	and not article_history.view_mode & ArticleViewModes.EDITABLE_BY_OTHERS \
	and not account_mgr.is_authorized(AccountManager.Roles.SUPERUSER) \
	and not article_history.article.owner_account.id == account_mgr.account_id:
		doc.add_message(u'Sorry, you may not view this article’s history')
		return True
	
	if action == ArticleActions.COMMENT_ON_TEXT \
	and not account_mgr.is_authorized(AccountManager.Roles.GUEST) \
	and not article_history.view_mode & ArticleViewModes.ALLOW_COMMENTS:
		doc.add_message(u'Sorry, you may not post comments on this article')
		return True
	
	if action == ArticleActions.EDIT_TEXT \
	and ((not account_mgr.is_authorized(AccountManager.Roles.SUPERUSER) \
	and article_history.article \
	and not article_history.article.owner_account.id == account_mgr.account_id) \
	or (not article_history.view_mode & ArticleViewModes.EDITABLE_BY_OTHERS \
	and not account_mgr.is_authorized(AccountManager.Roles.GUEST))):
		doc.add_message(u'Sorry, you may not edit this article')
		return True
	
	if action == ArticleActions.EDIT_TEXT_PROPERTIES \
	and (not account_mgr.is_authorized(AccountManager.Roles.OPERATOR) \
	and not article_history.article.owner_account.id == account_mgr.account_id):
		doc.add_message(u'Sorry, you may not edit this article’s properties')
		return True
	
	return False

class ArticleViewBase(BaseView):
	@classmethod
	def _html_article_text(cls, context, model):
		if model.text:
			doc_info = model.doc_info
			assert doc_info
			
			if doc_info.errors:
				yield lxmlbuilder.PRE(unicode(model.text))
			else:
				if doc_info.html_parts['docinfo']:
					yield lxml.html.fromstring(doc_info.html_parts['docinfo'])
				
				if doc_info.html_parts['fragment']:
					yield lxml.html.fromstring(doc_info.html_parts['fragment'])
	
	@classmethod
	def _html_article_title(cls, context, model):
		if model.text:
			doc_info = model.doc_info
			assert doc_info
			
			if doc_info.html_parts['body_pre_docinfo']:
				yield lxml.html.fromstring(doc_info.html_parts['body_pre_docinfo'])

	@classmethod
	def _html_article_brief_metadata(cls, context, model, is_nested_child):
		lion = Lion(context)
		
		major_box = HorizontalBox()
		
		for parent_model in model.parents:
			label = u'Re: %s' % (parent_model.title or parent_model.upload_filename or '(untitled')
			
			if is_nested_child:
				url = '#%s' % CMS.model_uuid_str(parent_model)
			else:
				url = context.str_url(fill_controller=True,
					args=[CMS.model_uuid_str(parent_model)],
				)
			
			major_box.children.append(Link(label=label, url=url))
		
		
		box = HorizontalBox()
		
		date = '(%s)' % lion.formatter.datetime(model.publish_date or model.date, 'short')
		box.children.append(Text(date))
		
		author_name = '(unknown)'
		
		if model._model.account and model._model.account.nickname:
			author_name = model._model.account.nickname
		
		super_users = frozenset([
			(AccountManager.Roles.NAMESPACE, AccountManager.Roles.ADMIN.code),
			(AccountManager.Roles.NAMESPACE, AccountManager.Roles.OPERATOR.code),
			(AccountManager.Roles.NAMESPACE, AccountManager.Roles.SUPERUSER.code),
		])
		
		roles = model._model.account.roles
		
		if not super_users.isdisjoint(frozenset(roles)):
			author_name = u'★ %s' % author_name
		
		box.children.append(Text(author_name))
		
		if model.version > 1:
			box.children.append(Text(u'(%d edits)' % model.version))
		
		yield major_box.render(context, 'html')
		yield box.render(context, 'html')
	
	@classmethod
	def _html_article_image(cls, context, model):
		url = context.str_url(fill_controller=True, 
				args=[CMS.model_uuid_str(model)], params=RAW)
			
		filename_mimetype = mimetypes.guess_type(model.metadata[ArticleMetadataFields.FILENAME])[0] or ''
		
		if filename_mimetype.find('image') != -1:
			yield lxmlbuilder.IMG(lxmlbuilder.CLASS('articleImage'), src=url)
		else:
			yield lxmlbuilder.A('Download', href=url)
	
	@classmethod
	def _html_article_detailed_metadata(cls, context, model):
		box = VerticalBox()
		box.children.append(Text('Article UUID: ' +model.article.uuid.urn))
		box.children.append(Text('Version UUID' +model.uuid.urn))
		
		if model.file:
			filename_mimetype = mimetypes.guess_type(model.metadata[ArticleMetadataFields.FILENAME])[0] or ''
			
			box.children.append(Text('Mimetype: %s' % filename_mimetype))
			box.children.append(Text('SHA256: %s' % model.file.hash.encode('hex')))
		
		yield box.render(context, 'html')
	
	@classmethod
	def _html_article_actions(cls, context, model):
		account_mgr = AccountManager(context)
		box = HorizontalBox()
		
		box.children.append(Link('Raw', context.str_url(
			args=[CMS.model_uuid_str(model)],
			params=RAW,
			fill_controller=True,
		)))
			
		if account_mgr.is_authorized(AccountManager.Roles.SUPERUSER) \
		or model.article.owner_account == account_mgr.account_model \
		or model.view_mode & ArticleViewModes.EDITABLE_BY_OTHERS:
			box.children.append(Link('Edit', context.str_url(
				args=[CMS.model_uuid_str(model.article)],
				params=EDIT if model.text else UPLOAD,
				fill_controller=True,
			)))
			
		if model.view_mode & ArticleViewModes.ALLOW_COMMENTS:
			if account_mgr.account_id:
				box.children.append(Link('Comment', context.str_url(
					args=[''],
					params=EDIT+NEW,
					fill_controller=True, 
						query=dict(parent=CMS.model_uuid_str(model.article))
				)))
			else:
				box.children.append(Text('Sign in to comment'))
			
			if account_mgr.is_authorized(AccountManager.Roles.USER):
				box.children.append(Link('Attach image', context.str_url(
					args=[''],
					params=UPLOAD+NEW,
					fill_controller=True, 
						query=dict(parent=CMS.model_uuid_str(model.article))
				)))
		if account_mgr.is_authorized(AccountManager.Roles.OPERATOR):
			box.children.append(Link('Admin', context.str_url(
				args=[CMS.model_uuid_str(model.article)],
				params=EDIT_VIEW,
				fill_controller=True,
			)))
		
		if model.view_mode & ArticleViewModes.EDITABLE_BY_OTHERS \
		or account_mgr.account_model == model.article.owner_account:
			box.children.append(Link('History', context.str_url(
				args=[CMS.model_uuid_str(model.article)],
				params=HISTORY,
				fill_controller=True,
			)))
		
		if model.version != model.article.current.version:
			box.children.append(Link(u'View current version', context.str_url(
				args=[CMS.model_uuid_str(model.article)],
				fill_controller=True,
			)))
		
		
		yield lxmlbuilder.E.aside(box.render(context, 'html'))
		

class ArticlePreviewView(ArticleViewBase):
	@classmethod
	def to_html(cls, context, model):
		element = lxmlbuilder.E.article(CLASS='article')
		
		element.extend(list(cls._html_article_title(context, model)))
		element.extend(list(cls._html_article_text(context, model)))
		
		return element

class ArticleSingleDetailView(ArticleViewBase):
	@classmethod
	def to_html(cls, context, model):
		element = lxmlbuilder.E.article(CLASS='article')
		element.set('id', CMS.model_uuid_str(model.article))
		
		r = ArticleViewBase._html_article_brief_metadata(context, model, False)
		element.extend(list(r))
		
		if model.text:
			element.extend(list(cls._html_article_text(context, model)))
		else:
			element.extend(list(cls._html_article_image(context, model)))
		
		element.extend(list(cls._html_article_detailed_metadata(context, model)))
		element.extend(list(cls._html_article_actions(context, model)))
		
		return element
		
class ArticleLinearView(ArticleViewBase):
	@classmethod
	def to_html(cls, context, model, offset=0, limit=50):
		box = lxmlbuilder.DIV()
		
		element = lxmlbuilder.E.article(CLASS='article')
		element.set('id', CMS.model_uuid_str(model.article))
		
		
		r = cls._html_article_brief_metadata(context, model, False)
		element.extend(list(r))
		
		if model.text:
			element.extend(list(cls._html_article_text(context, model)))
		else:
			element.extend(list(cls._html_article_image(context, model)))
		
		element.extend(list(cls._html_article_actions(context, model)))
		
		box.append(element)
		box.append(lxmlbuilder.BR())
		
		for child in model.article.get_children(offset=offset, limit=limit, 
		include_descendants=True):
			element = lxmlbuilder.E.article(CLASS='article')
			element.set('id', CMS.model_uuid_str(model))
		
			child = child.current
			r = cls._html_article_brief_metadata(context, child, False)
			element.extend(list(r))
			
			if child.text:
				element.extend(list(cls._html_article_text(context, child)))
			else:
				element.extend(list(cls._html_article_image(context, child)))
			
			element.extend(list(cls._html_article_actions(context, child)))
			
			box.append(element)

		return box
		
# TODO:
#class ArticleNestedView(ArticleViewBase):
#	@classmethod
#	def to_html(cls, context, model, nested_count=-1, is_nested_child=False, item_limit=50):
#		element = lxmlbuilder.E.article(CLASS='article')
#		
#		if nested_count > -1:
#			page_info = context.page_info(limit=item_limit)
#			children = model.article.get_children(page_info.offset, page_info.limit + 1)
#			
#			counter = 0
#			for child_article in children:
#				if counter < page_info.limit:
#					element.append(cls.to_html(context, child_article.current, 
#						nested_count=(nested_count - 1), is_nested_child=True,
#						item_limit=item_limit,
#						))
#				else:
#					page_info.more = True
#					
#				counter += 1
#			
#			if page_info.more or page_info.page > 1:
#				element.append(views.PagerView.to_html(context, page_info))
#			
#		elif is_nested_child and model.article.children:
#			element.append(lxmlbuilder.A('(More)', href=
#				context.str_url(
#				args=[CMS.model_uuid_str(model.article)],
#				fill_controller=True,)
#			))
#		
#		return element
	
	
	