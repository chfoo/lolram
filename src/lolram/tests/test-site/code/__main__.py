#encoding=utf8

import shutil
import contextlib
import wsgiref.util
import os.path

import lolram.app
import lolram.components.wui

ABCD = 'abcd'

class SiteApp(lolram.app.SiteApp):
	def init(self, fardel):
		self.router.set('/cleanup', self.delete_data)
		self.router.set('/session_test', self.session_test)
		self.router.set('/crash_test', self.crash_test)
		self.router.set('/serializer_test', self.serializer_test)
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
	
	def delete_data(self, fardel):
		# TODO
		fardel.resp.ok()
#		
#		with contextlib.closing(fardel.database.engine.connect()) as con:
#			trans = con.begin()
#			for table in reversed(fardel.database.metadata.sorted_tables):
#				con.execute(table.drop())
#			trans.commit()
#		
#		upload_dir = fardel.dirs.upload
#		
#		if os.path.exists(upload_dir):
#			shutil.rmtree(upload_dir)
		
		
	def session_test(self, fardel):
		fardel.resp.ok()
		if fardel.req.url.params == 'data':
			fardel.session.data.mydata = fardel.req.url.query.getfirst('data')
		elif fardel.req.url.params == 'persist':
			fardel.session.persistent = True
		elif fardel.req.url.params == 'get':
			return [str(fardel.session.data.mydata)]
	
	def crash_test(self, fardel):
		fardel.resp.ok()
		def f():
			yield 0 / 0
		return f()
	
	def serializer_test(self, fardel):
		fardel.resp.ok()
		fardel.data.nameStr = u'str ð'
		fardel.data.nameNum = 123456
		fardel.data.nameBool = True
		fardel.data.nameNone = None
		fardel.data.nameList = [1, 'a', False]
		fardel.data.nameDict = {'asdf':'n'}
	
	def not_found_test(self, fardel):
		fardel.resp.set_status(404, 'not found')
	
	def wui_basic_test(self, fardel):
		fardel.resp.ok()
		fardel.wui.title = 'my title'
		fardel.wui.meta.subtitle = 'my subtitle'
		fardel.wui.meta.author = 'chris'
		fardel.wui.meta.date = 'date'
		fardel.wui.scripts.append('scripts/test.js')
		fardel.wui.scripts.append('scripts/test2.js')
		fardel.wui.styles.append('styles/test.css')
		fardel.wui.styles.append('styles/test2.css')
		
	def form_test(self, fardel):
		form = lolram.components.wui.Form()
		
		form.group_start('group1')
		form.button('button1', 'button')
		form.group_end()
		form.textbox('textbox1', 'asdf')
		options = form.options('options1', 'asdf')
		options.option('option1', 'asdf')
		
		
		fardel.wui.content.append(form)
	
	def text_test(self, fardel):
		fardel.resp.ok()
		
		action = fardel.req.query.getfirst('action')
		
		if action == 'get':
			id = int(fardel.req.query.getfirst('id'))
			text = fardel.cms.get_text(id)
			yield text.encode('utf8') if text else 'not found'
		elif action == 'new':
			text = fardel.req.query.getfirst('text')
			yield str(fardel.cms.set_text(None, text))
		elif action == 'edit':
			text = fardel.req.query.getfirst('text')
			id = int(fardel.req.query.getfirst('id'))
			yield str(fardel.cms.set_text(id, text))
	
	def file_test(self, fardel):
		fardel.resp.ok()
		
		action = fardel.req.query.getfirst('action')
		
		if action == 'get':
			id = int(fardel.req.query.getfirst('id'))
			file_obj = fardel.cms.get_file(id)
			
			if file_obj:
				return wsgiref.util.FileWrapper(file_obj)
			else:
				return ['not found']
		
		elif action == 'new':
			file_obj = fardel.req.form['file'].file
			id = int(fardel.cms.add_file(file_obj))
			return [str(id)]
	
	def article_text_test(self, fardel):
		fardel.resp.ok()
		action = fardel.req.query.getfirst('action')
		
		if action == 'get':
			id = int(fardel.req.query.getfirst('id'))
			article = fardel.cms.get_article(id)
			return [article.text.encode('utf8')]
		elif action == 'new':
			text = fardel.req.query.getfirst('text')
			id = fardel.cms.save_article(None, text=text)
			return [str(id)]
		elif action == 'edit':
			text = fardel.req.query.getfirst('text')
			id = int(fardel.req.query.getfirst('id'))
			id = fardel.cms.save_article(id, text=text)
			return [str(id)]
		elif action == 'revision':
			id = int(fardel.req.query.getfirst('id'))
			revision = int(fardel.req.query.getfirst('revision'))
			article = fardel.cms.get_article(id)
			text = fardel.cms.get_text(
				tuple(article.get_history(revision, revision+1))[0].text_id)
			return [text.encode('utf8')]
	
	def article_file_test(self, fardel):
		fardel.resp.ok()
		action = fardel.req.query.getfirst('action')
		
		if action == 'get':
			id = int(fardel.req.query.getfirst('id'))
			article = fardel.cms.get_article(id)
			return wsgiref.util.FileWrapper(article.file)
		elif action == 'new':
			file_obj = fardel.req.form['file'].file
			filename = fardel.req.form['file'].filename
			id = fardel.cms.save_article(None, file_obj=file_obj, 
				filename=filename)
			return [str(id)]
		elif action == 'edit':
			file_obj = fardel.req.form['file'].file
			filename = fardel.req.form['file'].filename
			id = int(fardel.req.query.getfirst('id'))
			id = fardel.cms.save_article(id, file_obj=file_obj, 
				filename=filename)
			return [str(id)]
	
	def address_test(self, fardel):
		fardel.resp.ok()
		action = fardel.req.query.getfirst('action')
		
		if action == 'get':
			address = fardel.cms.get_address(
				fardel.req.query.getfirst('address'))
			return [str(address) if address is not None else 'not found']
		elif action == 'set':
			fardel.cms.set_address(fardel.req.query.getfirst('address'),
				int(fardel.req.query.getfirst('id')))
			return ['ok']
		elif action == 'delete':
			fardel.cms.delete_address(fardel.req.query.getfirst('address'))
			return ['ok']
	
	def article_tree_test(self, fardel):
		fardel.resp.ok()
		
		action = fardel.req.query.getfirst('action')
		article_id = int(fardel.req.query.getfirst('id'))
		article = fardel.cms.get_article(article_id)
		
		if action == 'get':
			children = list(article.get_children())
			
			return [str(children[0]) if children else 'not found']
		elif action == 'set':
			fardel.cms.add_child(article_id, int(fardel.req.query.getfirst('child')))
		elif action == 'delete':
			fardel.cms.remove_child(article_id, int(fardel.req.query.getfirst('child')))
			
	def account_basic_test(self, fardel):
		fardel.resp.ok()
		
		fardel.accounts.authenticate_testing_password(
			fardel.req.query.getfirst('password'))
		
		return ['ok' if fardel.accounts.account_id else 'fail']
