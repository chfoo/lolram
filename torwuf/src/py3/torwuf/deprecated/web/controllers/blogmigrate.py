'''Resolves queries from former blogger.com blog host

Thanks to the Google Data Liberation Front
'''
#
#    Copyright (c) 2012 Christopher Foo <chris.foo@gmail.com>
#
#    This file is part of Torwuf.
#
#    Torwuf is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Torwuf is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Torwuf.  If not, see <http://www.gnu.org/licenses/>.
#
from lolram.url import URL
from torwuf.deprecated.web.controllers.account.authorization.decorators import \
    require_admin
from torwuf.deprecated.web.models.cms import ArticleCollection, CommentCollection, \
    LegacyBlogLookupCollection
from torwuf.deprecated.web.utils import bytes_to_b32low_str
import iso8601
import json
import string
import torwuf.deprecated.web.controllers.base
import uuid

TITLE_CHARS = frozenset(string.ascii_letters + string.digits)


def canonicalize_title(title):
    title = title.lower()
    buffer_list = []

    for c in title:
        if c in TITLE_CHARS:
            buffer_list.append(c)

    return ''.join(buffer_list)


class BlogMigrateController(torwuf.deprecated.web.controllers.base.BaseController):
    def init(self):
        self.add_url_spec('/blog-migrate/url', TitleResolverHandler)
        self.add_url_spec('/blog-migrate/import', ImportHandler)


class TitleResolverHandler(torwuf.deprecated.web.controllers.base.BaseHandler):
    name = 'blog_migrate_title_resolver'

    def get(self):
        url = self.get_argument('q', '')

        if url.endswith('/feeds/posts/default'):
            self.redirect(self.reverse_url('cms_atom_feed'), permanent=True)
            return

        url_obj = URL(url)

        if url_obj.path.endswith('.html'):
            title = url_obj.path.rsplit('/', 1)[-1]
            title = title.replace('.html', '')

            title = canonicalize_title(title)

            result = self.app_controller.database[
                LegacyBlogLookupCollection.COLLECTION].find_one(
                {'_id': title}
            )

            if result:
                article_id = result[LegacyBlogLookupCollection.ARTICLE_ID]
                article = self.app_controller.database[
                    ArticleCollection.COLLECTION].find_one(
                        {'_id': article_id}
                    )

                self.redirect(self.reverse_url('cms_unique_item',
                    bytes_to_b32low_str(article[ArticleCollection.UUID].bytes)
                    ),
                    permanent=True)

                return

        self.redirect(self.reverse_url('cms_all_articles'))


class ImportHandler(torwuf.deprecated.web.controllers.base.BaseHandler):
    name = 'blog_migrate_import'

    @require_admin
    def get(self):
        self.render('blog_migrate/import.html')

    @require_admin
    def post(self):
        d = json.loads(self.request.field_storage['file'].file.read().decode())
        article_url_map = {}

        for post in d['posts']:
            new_article = {
                ArticleCollection.PRIVATE: True,
                ArticleCollection.PUBLICATION_DATE: iso8601.parse_date(
                    post['published']),
                ArticleCollection.TEXT: post['html'],
                ArticleCollection.TITLE: post['title'],
                ArticleCollection.UPDATED_DATE: iso8601.parse_date(
                    post['updated']),
                ArticleCollection.UUID: uuid.uuid4(),
                ArticleCollection.TAGS: ['blog'],
                ArticleCollection.RELATED_TAGS: [],
                ArticleCollection.LEGACY_ALLOW_RAW_HTML: True,
            }

            object_id = self.app_controller.database[
                ArticleCollection.COLLECTION].insert(new_article)
            article_url_map[post['url']] = object_id

            if post['url']:
                self.app_controller.database[
                    LegacyBlogLookupCollection.COLLECTION].insert(
                    {'_id': canonicalize_title(post['title']),
                    LegacyBlogLookupCollection.ARTICLE_ID: object_id
                    }
                )

        for comment in d['comments']:
            target_url = comment['url'].split('?')[0]

            new_comment = {
                CommentCollection.LEGACY_BLOGGER_ID:
                    comment['blogger_id'].split('/')[-1],
                CommentCollection.PUBLICATION_DATE:
                    iso8601.parse_date(post['published']),
                CommentCollection.TEXT: comment['html'],
#                CommentCollection.LEGACY_ALLOW_RAW_HTML: True,
                CommentCollection.ARTICLE_ID: article_url_map[target_url],
            }

            self.app_controller.database[CommentCollection.COLLECTION].insert(
                new_comment)

        self.render('blog_migrate/import.html')
