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

from lolram_deprecated_1.components import database
from lolram_deprecated_1.components.accounts.dbdefs import AccountsMeta
from lolram_deprecated_1.components.respool import ResPoolTextMeta, \
	ResPoolFileMeta
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import Integer, DateTime, Unicode, LargeBinary
import datetime
import sqlalchemy.orm.session
import uuid

__docformat__ = 'restructuredtext en'


#class ActionRole(object):
#	NAMESPACE = 'lr-cms'
#	VIEWER = 1
#	COMMENTER = 3
#	WRITER = 4
#	MODERATOR = 5
#	CURATOR = 6
#	BUREAUCRAT = 7
#	BOT = 8


class ArticleViewModes(object):
	VIEWABLE = 0b1
	FILE = 0b10
	EDITABLE_BY_OTHERS = 0b100
	ALLOW_COMMENTS = 0b1000
	CATEGORY = 0b10000


class ArticleActions(object):
	COMMENT_ON_TEXT = 'comment'
	EDIT_TEXT = 'edit'
	VIEW_TEXT = 'view'
	EDIT_TEXT_PROPERTIES = 'edit-properties'
	VIEW_HISTORY = 'view-history'


class ArticleMetadataFields(object):
	PUBLISH_DATE = 'pubdate'
	TITLE = 'title'
	FILENAME = 'filename'
#	MIMETYPE = 'mimetype'
#	FILETYPE = 'filetype'
	PARENTS = 'parents'
	ADDRESSES = 'addresses'
	VIEW_MODE = 'viewmode'
	PRIMARY_ADDRESS = 'primaddr'


class CMSArticlesMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSArticle(database.TableMeta.Def.base()):
			__tablename__ = 'cms_articles'
			
			id = Column(Integer, primary_key=True) #@ReservedAssignment
			account_id = Column(ForeignKey(AccountsMeta.D1.Account.id))
			account = relationship(AccountsMeta.D1.Account)
			date = Column(DateTime, default=datetime.datetime.utcnow)
			title = Column(Unicode(length=160))
			uuid = Column(LargeBinary(length=16), default=lambda:uuid.uuid4().bytes, index=True)
			view_mode = Column(Integer)
			version = Column(Integer, nullable=False)
			primary_address = Column(Unicode(length=160))
		
		desc = 'new table'
		model = CMSArticle
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)

	uuid = 'urn:uuid:f9d34d49-5226-48a1-a115-3c07de711071'
	defs = (D1, )

ResPoolText = ResPoolTextMeta.D1.ResPoolText
ResPoolFile = ResPoolFileMeta.D1.ResPoolFile

class CMSHistoryMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSHistory(database.TableMeta.Def.base()):
			__tablename__ = 'cms_history'
			
			article_id = Column(ForeignKey(CMSArticlesMeta.D1.CMSArticle.id),
				primary_key=True)
			article = relationship(CMSArticlesMeta.D1.CMSArticle)
			version = Column(Integer, primary_key=True)
			text_id = Column(ForeignKey(ResPoolText.id))
			data_id = Column(ForeignKey(ResPoolText.id))
			file_id = Column(ForeignKey(ResPoolFile.id))
			reason = Column(ForeignKey(ResPoolText.id))
			created = Column(DateTime, default=datetime.datetime.utcnow)
			uuid = Column(LargeBinary(length=16), default=lambda:uuid.uuid4().bytes, index=True)
			account_id = Column(ForeignKey(AccountsMeta.D1.Account.id))
			account = relationship(AccountsMeta.D1.Account)
			
		desc = 'new table'
		model = CMSHistory
	
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)

	uuid = 'urn:uuid:597f9776-3e38-4c91-87fd-295f1b8ab29d'
	defs = (D1,)


class CMSAddressesMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSAddress(database.TableMeta.Def.base()):
			__tablename__ = 'cms_addresses'
			
			id = Column(Integer, primary_key=True) #@ReservedAssignment
			name = Column(Unicode(length=160), nullable=False, unique=True, index=True)
			article_id = Column(ForeignKey(CMSArticlesMeta.D1.CMSArticle.id),
				nullable=False)
			article = relationship(CMSArticlesMeta.D1.CMSArticle, 
				collection_class=set)
		
		desc = 'new table'
		model = CMSAddress
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)

	uuid = 'urn:uuid:02e2bb62-81c2-4b50-8417-e26d3011da61'
	defs = (D1,)


class CMSArticleTreeMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSArticleTree(database.TableMeta.Def.base()):
			__tablename__ = 'cms_article_tree'
			
			article_id = Column(ForeignKey(CMSArticlesMeta.D1.CMSArticle.id), 
				primary_key=True)
			article = relationship(CMSArticlesMeta.D1.CMSArticle,
				primaryjoin=article_id==CMSArticlesMeta.D1.CMSArticle.id)
			parent_article_id = Column(ForeignKey(CMSArticlesMeta.D1.CMSArticle.id),
				primary_key=True)
			parent_article = relationship(CMSArticlesMeta.D1.CMSArticle,
				primaryjoin=article_id==CMSArticlesMeta.D1.CMSArticle.id)
			
			@property
			def children(self):
				session = sqlalchemy.orm.session.Session.object_session(self)
				query = session.query(self.__class__) \
					.filter_by(parent_article_id=self.article_id)
				return query
	
		desc = 'new table'
		model = CMSArticleTree
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)
		


	uuid = 'urn:uuid:b4227b69-c4ce-47e6-910a-e5b9f7c1f8df'
	defs = (D1,)


class CMSArticleMPTreeMeta(database.TableMeta):
	class D1(database.TableMeta.Def):
		class CMSArticleMPTree(database.TableMeta.Def.base()):
			__tablename__ = 'cms_article_mp_tree'
			__mp_manager__ = 'mp'
			
			id = Column(Integer, primary_key=True) #@ReservedAssignment
			parent_id = Column(ForeignKey('cms_article_mp_tree.id'))
			parent = relationship("CMSArticleMPTree", remote_side=[id])
			article_id = Column(ForeignKey(CMSArticlesMeta.D1.CMSArticle.id),
				index=True, nullable=False)
			article = relationship(CMSArticlesMeta.D1.CMSArticle,
				primaryjoin=article_id==CMSArticlesMeta.D1.CMSArticle.id)
	
		desc = 'new table'
		model = CMSArticleMPTree
		
		def upgrade(self, engine, session):
			self.model.__table__.create(engine)
		
		def downgrade(self, engine, session):
			self.model.__table__.drop(engine)
	
	uuid = 'urn:uuid:a4f2cdf9-3515-49e9-8b73-ed251acdd816'
	defs = (D1,)
