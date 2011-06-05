#encoding=utf8

import shutil
import contextlib
import wsgiref.util
import os.path

import lolram.app
import lolram.components.wui
import lolram.components.session
import lolram.components.accounts
import lolram.components.cms
import lolram.components.database

ABCD = 'abcd'

class SiteApp(lolram.app.SiteApp):
	def init(self):
		self.router.set('/cleanup', self.delete_data)
		self.router.set('/session_test', self.session_test)
		self.router.set('/crash_test', self.crash_test)
		self.router.set_default(self.not_found_test)
		self.router.set('/wui_basic_test', self.wui_basic_test)
		self.router.set('/form_test', self.form_test)
		self.router.set('/text_test', self.text_test)
		self.router.set('/file_test', self.file_test)
		self.router.set('/article_text_test', self.article_text_test)
		self.router.set('/article_file_test', self.article_file_test)
		self.router.set('/address_test', self.address_test)
		self.router.set('/article_tree_test', self.article_tree_test)
		self.router.set('/account_basic_test', self.account_basic_test)
	
	def delete_data(self):
		self.context.logger.info(u'Request to delete test db rows and data')
		self.context.response.ok()
		db = self.context.get_instance(lolram.components.database.Database)
		
		for model_name in dir(db.models):
			if model_name.startswith('_'):
				continue
			
			model = db.models.__dict__[model_name]
			self.context.logger.debug(u'Delete row %s' % model)
			
			db.session.query(model).delete()
			
			
		
		upload_dir = self.context.dirinfo.upload
		
		if os.path.exists(upload_dir):
			shutil.rmtree(upload_dir)
			os.mkdir(upload_dir)
		
	def session_test(self):
		session = self.context.get_instance(lolram.components.session.Session)
		self.context.response.ok()
		if self.context.request.url.params == 'data':
			session.data.mydata = self.context.request.url.query.getfirst('data')
		elif self.context.request.url.params == 'persist':
			session.persistent = True
		elif self.context.request.url.params == 'get':
			return [str(session.data.mydata)]
	
	def crash_test(self):
		self.context.response.ok()
		def f():
			yield 0 / 0
		return f()
	
	def not_found_test(self):
		self.context.response.set_status(404)
	
	def wui_basic_test(self):
		self.context.response.ok()
		doc = self.context.get_instance(lolram.components.wui.Document)
		doc.title = 'my title'
		doc.meta.subtitle = 'my subtitle'
		doc.meta.author = 'chris'
		doc.meta.date = 'date'
		doc.scripts.append('scripts/test.js')
		doc.scripts.append('scripts/test2.js')
		doc.styles.append('styles/test.css')
		doc.styles.append('styles/test2.css')
		
	def form_test(self):
		form = lolram.components.wui.Form()
		doc = self.context.get_instance(lolram.components.wui.Document)
		
		form.group_start('group1')
		form.button('button1', 'button')
		form.group_end()
		form.textbox('textbox1', 'asdf')
		options = form.options('options1', 'asdf')
		options.option('option1', 'asdf')
		
		
		doc.append(form)
	
	def text_test(self):
		self.context.response.ok()
		cms = self.context.get_instance(lolram.components.cms.CMS)
		
		action = self.context.request.query.getfirst('action')
		
		if action == 'get':
			id = int(self.context.request.query.getfirst('id'))
			text = cms._get_text(id)
			yield text.encode('utf8') if text else 'not found'
		elif action == 'new':
			text = self.context.request.query.getfirst('text')
			yield str(cms._set_text(None, text))
		elif action == 'edit':
			text = self.context.request.query.getfirst('text')
			id = int(self.context.request.query.getfirst('id'))
			yield str(cms._set_text(id, text))
	
	def file_test(self):
		self.context.response.ok()
		cms = self.context.get_instance(lolram.components.cms.CMS)
		
		action = self.context.request.query.getfirst('action')
		
		if action == 'get':
			id = int(self.context.request.query.getfirst('id'))
			file_obj = cms._get_file(id)
			
			if file_obj:
				return wsgiref.util.FileWrapper(file_obj)
			else:
				return ['not found']
		
		elif action == 'new':
			file_obj = self.context.request.form['file'].file
			id = int(cms._add_file(file_obj))
			return [str(id)]
	
	def article_text_test(self):
		self.context.response.ok()
		action = self.context.request.query.getfirst('action')
		cms = self.context.get_instance(lolram.components.cms.CMS)
		
		if action == 'get':
			id = int(self.context.request.query.getfirst('id'))
			article = cms.get_article(id)
			return [article.text.encode('utf8')]
		elif action == 'new':
			text = self.context.request.query.getfirst('text')
			article = cms.new_article()
			article.text = text
			article.save('new')
			id = article.id
			return [str(id)]
		elif action == 'edit':
			text = self.context.request.query.getfirst('text')
			id = int(self.context.request.query.getfirst('id'))
			article = cms.get_article(id)
			article.text = text
			article.save('edit')
			return [str(id)]
		elif action == 'revision':
			id = int(self.context.request.query.getfirst('id'))
			revision = int(self.context.request.query.getfirst('revision'))
			article = cms.get_histories(revision, 1, article_id=id)[0]
			text = article.text
			return [text.encode('utf8')]
	
	def article_file_test(self):
		self.context.response.ok()
		action = self.context.request.query.getfirst('action')
		cms = self.context.get_instance(lolram.components.cms.CMS)
		
		if action == 'get':
			id = int(self.context.request.query.getfirst('id'))
			article = cms.get_article(id)
			return wsgiref.util.FileWrapper(article.file)
		elif action == 'new':
			file_obj = self.context.request.form['file'].file
			filename = self.context.request.form['file'].filename
			article = cms.new_article()
			article.set_file(file_obj=file_obj, upload_filename=filename)
			article.save()
			id = article.id
			return [str(id)]
		elif action == 'edit':
			file_obj = self.context.request.form['file'].file
			filename = self.context.request.form['file'].filename
			id = int(self.context.request.query.getfirst('id'))
			article = cms.get_article(id)
			article.set_file(file_obj=file_obj, upload_filename=filename)
			article.save()
			id = article.id
			return [str(id)]
	
	def address_test(self):
		self.context.response.ok()
		action = self.context.request.query.getfirst('action')
		cms = self.context.get_instance(lolram.components.cms.CMS)
		address = self.context.request.query.getfirst('address')
		
		if action == 'get':
			article = cms.get_article(address=address)
			if article:
				return [str(article.id)]
			else:
				return ['not found']
		elif action == 'set':
			article = cms.get_article(int(self.context.request.query.getfirst('id')))
			article.addresses = article.addresses | set([address])
			article.save()
			return ['ok']
		elif action == 'delete':
			article = cms.get_article(address=address)
			article.addresses = article.addresses - set([address])
			article.save()
			return ['ok']
	
	def article_tree_test(self):
		self.context.response.ok()
		
		cms = self.context.get_instance(lolram.components.cms.CMS)
		action = self.context.request.query.getfirst('action')
		article_id = int(self.context.request.query.getfirst('id'))
		article = cms.get_article(article_id)
		
		if action == 'get':
			return [str(tuple(article.children)[0].id) if article.children else 'not found']
		elif action == 'set':
			child_id = int(self.context.request.query.getfirst('child'))
			child = cms.get_article(child_id)
			child.parents = child.parents | set([article])
			child.save()
		elif action == 'delete':
			child_id = int(self.context.request.query.getfirst('child'))
			child = cms.get_article(child_id)
			child.parents = child.parents - set([article])
			child.save()
			
	def account_basic_test(self):
		self.context.response.ok()
		
		acc = self.context.get_instance(lolram.components.accounts.Accounts)
		
		acc.authenticate_testing_password(
			self.context.request.query.getfirst('password'))
		
		return ['ok' if acc.account_id else 'fail']
