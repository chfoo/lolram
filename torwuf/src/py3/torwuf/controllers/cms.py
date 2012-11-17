'''Content management system controller (blog, articles, files, etc)'''
# This file is part of Torwuf.
# Copyright © 2012 Christopher Foo <chris.foo@gmail.com>.
# Licensed under GNU GPLv3. See COPYING.txt for details.
from pywheel.backoff import Trier
from pywheel.db.mongodb import AggregateTagsCode
from tornado.web import HTTPError, URLSpec
from torwuf import restdoc
from torwuf.controllers.base import (tag_list_to_str, require_admin,
    BaseRequestHandler, b32low_str_to_bytes, bytes_to_b32low_str)
from torwuf.models.cms import (ArticleCollection, TagCollection,
    TagCountCollection)
import base64
import bson
import datetime
import hashlib
import http.client
import io
import isodate
import logging
import mimetypes
import os.path
import pymongo
import shlex
import subprocess
import tempfile
import uuid

_logger = logging.getLogger(__name__)


class CMSController(object):
    def __init__(self, application):
        self.application = application
        Trier(self._setup_index)

    @property
    def article_collection(self):
        return self.application.db[ArticleCollection.COLLECTION]

    @property
    def tag_collection(self):
        return self.application.db[TagCollection.COLLECTION]

    def _setup_index(self):
        self.article_collection.ensure_index(
            [(ArticleCollection.TAGS, pymongo.ASCENDING)])
        self.article_collection.ensure_index(
            [(ArticleCollection.RELATED_TAGS, pymongo.ASCENDING)])
        self.article_collection.ensure_index(
            [(ArticleCollection.UUID, pymongo.ASCENDING)], unique=True)

    def render_text(self, text):
        doc_info = restdoc.publish_text(text)

        return doc_info

    def generate_tag_count_collection(self):
        _logger.info('Generating tag collection')

        self.article_collection.map_reduce(
            AggregateTagsCode.make_map_tags_code(),
            AggregateTagsCode.make_reduce_tags_code(),
            out=TagCountCollection.COLLECTION)

        results = self.application.db[TagCountCollection.COLLECTION].find()

        for result in results:
            self.update_tag_count(result['_id'],
                result[TagCountCollection.COUNT])

    def update_tag_count(self, tag_id, count, increment=False):
        if increment:
            self.tag_collection.update({'_id': tag_id},
                {'$inc': {TagCollection.COUNT: count}}
            )
        else:
            self.tag_collection.update({'_id': tag_id},
                {'$set': {TagCollection.COUNT: count}},
                upsert=True,
            )


class HandlerMixin(object):
    @property
    def article_collection(self):
        return self.application.db[ArticleCollection.COLLECTION]

    @property
    def tag_collection(self):
        return self.application.db[TagCollection.COLLECTION]

    def get_disk_file_path(self, hash_str):
        hash_str = hash_str.lower()
        return os.path.join(self.application.upload_path, 'cms',
            hash_str[0:2], hash_str[2:4], hash_str[4:6], hash_str)

    def serve_nginx_file(self, path):
        file_path = path.replace(self.application.upload_path, '').lstrip('/')
        file_path = '/uploads/{}'.format(file_path)
        self.set_header('X-Accel-Redirect', file_path)


class UniqueItemHandler(BaseRequestHandler, HandlerMixin):
    name = 'cms_unique_item'

    def get(self, b32_str):
        uuid_obj = uuid.UUID(bytes=b32low_str_to_bytes(b32_str))
        result = self.article_collection.find_one(
            {ArticleCollection.UUID: uuid_obj})

        # FIXME:
        if result and result.get(ArticleCollection.PRIVATE):
#        and (not self.app_controller.controllers['AuthorizationController'].\
#        is_admin_account(self.current_user) \
#        and not self.get_current_user() == 'test:localhost'):
            raise HTTPError(http.client.FORBIDDEN)
        elif result and ArticleCollection.FILE_SHA1 not in result:
            self.do_article(result)
        elif result:
            self.do_file(result)
        else:
            raise HTTPError(http.client.NOT_FOUND)

    def do_article(self, result):
        rest_doc = self.application.cms.render_text(
            result[ArticleCollection.TEXT])

        if result.get(ArticleCollection.RELATED_TAGS):
            query = {
                ArticleCollection.TAGS: result[ArticleCollection.RELATED_TAGS],
                ArticleCollection.FILE_SHA1: {'$exists': True},
            }
            related_files = list(self.article_collection.find(query,
                sort=[(ArticleCollection.PUBLICATION_DATE, pymongo.ASCENDING)]
            ))
        else:
            related_files = []

        self.render('cms/view_article.html', article=result,
            rest_doc=rest_doc,
            related_files=related_files,
            ArticleCollection=ArticleCollection)

    def do_file(self, result):
        if result[ArticleCollection.TAGS]:
            query = {
                ArticleCollection.TAGS: result[ArticleCollection.TAGS],
                ArticleCollection.FILE_SHA1: {'$exists': False},
            }
            related_articles = list(self.article_collection.find(query,
                sort=[(ArticleCollection.PUBLICATION_DATE, pymongo.ASCENDING)]
            ))
        else:
            related_articles = []

        if result[ArticleCollection.TAGS]:
            query = {
                ArticleCollection.TAGS: result[ArticleCollection.TAGS],
                ArticleCollection.FILE_SHA1: {'$exists': True},
            }
            related_files = list(self.article_collection.find(query,
                sort=[(ArticleCollection.PUBLICATION_DATE, pymongo.ASCENDING)]
            ))

            prev_article, next_article = self.find_prev_and_next(
                result[ArticleCollection.UUID], related_files)

        else:
            prev_article = None
            next_article = None

        self.render('cms/view_file.html', article=result,
            related_articles=related_articles,
            prev_article=prev_article,
            next_article=next_article,
            ArticleCollection=ArticleCollection)

    def find_prev_and_next(self, target_uuid_obj, related_articles):
        related_uuids = [article[ArticleCollection.UUID] \
            for article in related_articles]

        index = related_uuids.index(target_uuid_obj)

        if index > 0:
            prev_index = index - 1
            prev_article = related_articles[prev_index]
        else:
            prev_article = None

        if index < len(related_uuids) - 1:
            next_index = index + 1
            next_article = related_articles[next_index]
        else:
            next_article = None

        return (prev_article, next_article)


class DownloadHandler(BaseRequestHandler, HandlerMixin):
    name = 'cms_download'

    def get(self, b32_str):
        uuid_obj = uuid.UUID(bytes=b32low_str_to_bytes(b32_str))
        result = self.article_collection.find_one(
            {ArticleCollection.UUID: uuid_obj})

        if result and result.get(ArticleCollection.PRIVATE):
            raise HTTPError(http.client.FORBIDDEN)
        elif ArticleCollection.FILE_SHA1 in result:
            self.do_file_download(result)
        else:
            self.set_header('Content-Type', 'text/plain; encoding=utf-8')
            self.write(result[ArticleCollection.TEXT])
            self.finish()
            return

    def head(self, b32_str):
        uuid_obj = uuid.UUID(bytes=b32low_str_to_bytes(b32_str))
        result = self.article_collection.find_one(
            {ArticleCollection.UUID: uuid_obj})

        if ArticleCollection.FILE_SHA1 in result:
            self.do_file_download(result, include_body=False)
        else:
            raise HTTPError(http.client.BAD_REQUEST)

    def do_file_download(self, result, include_body=True):
        path = base64.b16encode(result[ArticleCollection.FILE_SHA1]).decode()

        if result[ArticleCollection.FILENAME]:
            filename = result[ArticleCollection.FILENAME]
            file_type, encoding = mimetypes.guess_type(filename)

            if file_type:
                self.set_header('Content-Type', file_type)

        else:
            filename = None

        # FIXME:
#        self.serve_file(self.get_disk_file_path(path), filename=filename,
#            include_body=include_body)
        self.set_header('Content-Disposition',
            'attachment; filename={}'.format(filename.strip('\r\n')))
#        self.set_header('X-Sendfile', self.get_disk_file_path(path))
        self.serve_nginx_file(self.get_disk_file_path(path))


class ResizeHandler(BaseRequestHandler, HandlerMixin,):
    name = 'cms_resize'
    SIZE_THUMBNAIL = 75
    SIZE_PREVIEW = 500
    SIZE_LARGE = 1000

    def get_thumbnail_path(self, hash_str, suffix):
        if '/' in suffix:
            raise Exception('Bad suffix (Slash deliminator not allowed)')

        hash_str = hash_str.lower()
        return os.path.join(self.application.upload_path,
            'cms_thumbnails', hash_str[0:2], hash_str[2:4], hash_str[4:6],
            hash_str + suffix)

    def get(self, b32_str, resize_method):
        uuid_obj = uuid.UUID(bytes=b32low_str_to_bytes(b32_str))
        result = self.article_collection.find_one(
            {ArticleCollection.UUID: uuid_obj})

        if ArticleCollection.FILE_SHA1 in result:
            self.do_file_download(result, resize_method)
        else:
            raise HTTPError(http.client.BAD_REQUEST)

    def head(self, b32_str, resize_method):
        uuid_obj = uuid.UUID(bytes=b32low_str_to_bytes(b32_str))
        result = self.article_collection.find_one(
            {ArticleCollection.UUID: uuid_obj})

        if ArticleCollection.FILE_SHA1 in result:
            self.do_file_download(result, resize_method, include_body=False)
        else:
            raise HTTPError(http.client.BAD_REQUEST)

    def do_file_download(self, article, resize_method, include_body=True):
        if resize_method == 'thumbnail':
            size = ResizeHandler.SIZE_THUMBNAIL
        elif resize_method == 'preview':
            size = ResizeHandler.SIZE_PREVIEW
        elif resize_method == 'large':
            size = ResizeHandler.SIZE_LARGE
        else:
            raise HTTPError(http.client.BAD_REQUEST,
                'unknown size {}'.format(resize_method))

        hash_str = base64.b16encode(article[ArticleCollection.FILE_SHA1]
            ).decode().lower()
        source_path = self.get_disk_file_path(hash_str)
        dest_path = self.get_thumbnail_path(hash_str, str(size))

        if article[ArticleCollection.FILENAME]:
            filename = article[ArticleCollection.FILENAME]

            if filename.endswith('.svg'):
                self.set_header('Content-Type', 'image/svg+xml')

                dest_path += '.svg.png'
            else:
                file_type, encoding = mimetypes.guess_type(filename)

                if file_type:
                    self.set_header('Content-Type', file_type)

            if not os.path.exists(dest_path):
                self.resize(source_path, dest_path, size)

        # FIXME:
#        self.serve_file(dest_path, include_body=include_body)
#        self.set_header('X-Sendfile', dest_path)
        self.serve_nginx_file(dest_path)

    def resize(self, source_path, dest_path, size):
        _logger.debug('Attempt convert %s to %s size %s', source_path,
            dest_path, size)

        dest_dir = os.path.dirname(dest_path)

        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        # rsvg-convert doesn't support advanced sizes, it also appears
        # that imagemagick uses librsvg anyway
        program_name = 'imagemagick'
        args = ['convert', source_path, '-resize',
            '{}x{}>'.format(size, size), dest_path]

        if dest_path.endswith('.svg.png'):
            args.insert(1, '-background')
            args.insert(2, 'none')

        p = subprocess.Popen(args)

        return_code = p.wait()

        if return_code:
            raise HTTPError(http.client.INTERNAL_SERVER_ERROR,
                '{} convert gave error code {}'.format(program_name,
                    return_code))


class BaseEditArticleHandler(BaseRequestHandler, HandlerMixin):
    def new_form_data(self):
        return dict(
            uuid=uuid.uuid4(),
            date=datetime.datetime.utcnow().isoformat(),
            title='',
            tags='',
            text='',
            related_tags='',
            private=False,
            raw_html=False,
        )

    def get_form_data(self, hex_id):
        object_id = bson.objectid.ObjectId(hex_id)

        result = self.article_collection.find_one({'_id': object_id})

        if result:
            return dict(
                uuid=result[ArticleCollection.UUID],
                date=result[ArticleCollection.PUBLICATION_DATE].isoformat(),
                title=result[ArticleCollection.TITLE],
                tags=tag_list_to_str(result[ArticleCollection.TAGS]),
                text=result[ArticleCollection.TEXT],
                related_tags=tag_list_to_str(
                    result[ArticleCollection.RELATED_TAGS]),
                private=result.get(ArticleCollection.PRIVATE, False),
                raw_html=result.get(ArticleCollection.LEGACY_ALLOW_RAW_HTML,
                    False)
            )

    def save(self, object_id=None):

        title = self.get_argument('title', None)
        text = self.get_argument('text', None)
        # TODO: remove duplicates with sets
        tags = shlex.split(self.get_argument('tags', ''))
        related_tags = shlex.split(self.get_argument('related_tags', ''))
        private = self.get_argument('private', None) == 'private'
        raw_html = self.get_argument('raw_html', None) == 'raw_html'

        rest_doc = self.application.cms.render_text(text)

        if not title and rest_doc.title:
            # FIXME:
#            self.add_message('Title automatically parsed from document')

            title = rest_doc.title

        if not self.get_argument('uuid', None) and rest_doc.meta.get('uuid'):
#            self.add_message('UUID automatically parsed from document')

            uuid_obj = uuid.UUID(rest_doc.meta.get('uuid'))
        else:
            uuid_obj = uuid.UUID(self.get_argument('uuid'))

        publication_date = None

        if not self.get_argument('date', None) and rest_doc.meta.get('date'):
            try:
                publication_date = isodate.parse_datetime(rest_doc.meta['date'])

                self.add_message('Date automatically parsed from document')
            except isodate.ISO8601Error:
                pass

        if not publication_date and self.get_argument('date', None):
            publication_date = isodate.parse_datetime(self.get_argument('date'))
        elif not publication_date:
            publication_date = datetime.datetime.utcnow()

        form_data = dict(
            uuid=uuid_obj,
            date=publication_date,
            title=title,
            tags=tag_list_to_str(tags),
            text=text,
            rest_doc=rest_doc,
            related_tags=tag_list_to_str(related_tags),
            private=private,
            raw_html=raw_html,
        )

        if self.get_argument('save', False) != False:
            d = {
                ArticleCollection.PUBLICATION_DATE: publication_date,
                ArticleCollection.TAGS: tags,
                ArticleCollection.TITLE: title,
                ArticleCollection.TEXT: text,
                ArticleCollection.UUID: uuid_obj,
                ArticleCollection.RELATED_TAGS: related_tags,
                ArticleCollection.PRIVATE: private,
                ArticleCollection.LEGACY_ALLOW_RAW_HTML: raw_html,
            }

            if object_id:
                d['_id'] = object_id
                self.article_collection.save(d)
            else:
                object_id = self.article_collection.insert(d)

            # TODO: just update the tag counts here
            self.application.cms.generate_tag_count_collection()

            # FIXME:
#            self.add_message('Article saved')

            id_str = bytes_to_b32low_str(uuid_obj.bytes)
            self.redirect(self.reverse_url(UniqueItemHandler.name, id_str),
                status=http.client.SEE_OTHER)
#                , api_data={
#                    'id': object_id,
#                    'uuid': uuid_obj,
#                })
        else:
            self.render('cms/edit_article.html', **form_data)


class NewArticleHandler(BaseEditArticleHandler):
    name = 'cms_article_new'

    @require_admin
    def get(self):
        form_data = self.new_form_data()

        self.render('cms/edit_article.html', **form_data)

    @require_admin
    def post(self):
        self.save()


class EditArticleHandler(BaseEditArticleHandler):
    name = 'cms_article_edit'

    @require_admin
    def get(self, hex_id):
        form_data = self.get_form_data(hex_id)

        self.render('cms/edit_article.html', **form_data)

    @require_admin
    def post(self, hex_id):
        object_id = bson.objectid.ObjectId(hex_id)
        self.save(object_id)


class DeleteArticleHandler(BaseRequestHandler, HandlerMixin):
    name = 'cms_article_delete'

    @require_admin
    def get(self, hex_id):
        object_id = bson.objectid.ObjectId(hex_id)
        result = self.article_collection.find_one({'_id': object_id})

        if result:
            self.render('cms/delete_article',
                title=result[ArticleCollection.TITLE],
                confirm_key=self.generate_confirm_key(object_id))
        else:
            raise HTTPError(http.client.NOT_FOUND)

    @require_admin
    def post(self, hex_id):
        object_id = bson.objectid.ObjectId(hex_id)
        result = self.article_collection.find_one({'_id': object_id})
        confirmed = self.get_argument('confirm', False) is not False

        if result and confirmed:
            self.article_collection.remove({'_id': object_id})
            # FIXME:
#            self.add_message('Article deleted')
            self.redirect('/', api_data={})
        elif result:
            HTTPError(http.client.BAD_REQUEST, 'bad confirm key')
        else:
            raise HTTPError(http.client.NOT_FOUND)


class BaseEditFileHandler(BaseRequestHandler, HandlerMixin):
    def save_to_disk(self, file_obj):
        with tempfile.TemporaryDirectory() as dir_path:
            dest_temp_path = os.path.join(dir_path, 'file')
            dest_file = open(dest_temp_path, 'wb')
            hash_obj = hashlib.sha1()

            while True:
                data = file_obj.read(4096)

                if data == b'':
                    break

                hash_obj.update(data)
                dest_file.write(data)

            dest_path = self.get_disk_file_path(hash_obj.hexdigest())

            if not os.path.exists(dest_path):
                os.makedirs(os.path.dirname(dest_path))
                os.rename(dest_temp_path, dest_path)

        return hash_obj.digest()

    def new_form_data(self):
        return dict(
            uuid=uuid.uuid4(),
            date=datetime.datetime.utcnow(),
            title='',
            tags='',
            text='',
        )

    def get_form_data(self, hex_id):
        object_id = bson.objectid.ObjectId(hex_id)

        result = self.article_collection.find_one({'_id': object_id})

        if result:
            return dict(
                uuid=result[ArticleCollection.UUID],
                date=result[ArticleCollection.PUBLICATION_DATE],
                title=result[ArticleCollection.TITLE],
                tags=tag_list_to_str(result[ArticleCollection.TAGS]),
                text=result[ArticleCollection.TEXT],
            )

    def save(self, object_id=None):

        title = self.get_argument('title', None)
        text = self.get_argument('text', None)
        publication_date = isodate.parse_datetime(self.get_argument('date', None))
        tags = shlex.split(self.get_argument('tags', ''))
        uuid_obj = uuid.UUID(self.get_argument('uuid'))

        if object_id is None:
            file_obj = io.BytesIO(self.request.files['file'][0].body)
            filename = self.request.files['file'][0].filename
            sha1 = self.save_to_disk(file_obj)

            if not title:
                title = filename

            object_id = self.article_collection.insert({
                ArticleCollection.FILENAME: filename,
                ArticleCollection.PUBLICATION_DATE: publication_date,
                ArticleCollection.FILE_SHA1: sha1,
                ArticleCollection.TAGS: tags,
                ArticleCollection.TEXT: text,
                ArticleCollection.TITLE: title,
                ArticleCollection.UUID: uuid_obj,
            })
        else:
            update_dict = {
                ArticleCollection.PUBLICATION_DATE: publication_date,
                ArticleCollection.TAGS: tags,
                ArticleCollection.TEXT: text,
                ArticleCollection.TITLE: title,
                ArticleCollection.UUID: uuid_obj,
            }

            if 'file' in self.request.files \
            and self.request.files['file'][0].filename:
                file_obj = io.BytesIO(self.request.files['file'][0].body)
                filename = self.request.files['file'][0].filename
                sha1 = self.save_to_disk(file_obj)

                update_dict[ArticleCollection.FILENAME] = filename
                update_dict[ArticleCollection.FILE_SHA1] = sha1

            self.article_collection.update({'_id': object_id},
                {'$set': update_dict}
            )

        self.application.cms.generate_tag_count_collection()
        # FIXME:
#        self.add_message('File saved')
        self.redirect(self.reverse_url(UniqueItemHandler.name,
            bytes_to_b32low_str(uuid_obj.bytes)))


class UploadFileHandler(BaseEditFileHandler):
    name = 'cms_file_upload'

    @require_admin
    def get(self):
        self.render('cms/upload_file.html', **self.new_form_data())

    @require_admin
    def post(self):
        self.save()


class EditFileHandler(BaseEditFileHandler):
    name = 'cms_file_edit'

    @require_admin
    def get(self, hex_id):
        form_data = self.get_form_data(hex_id)

        if form_data:
            self.render('cms/upload_file.html', **form_data)
        else:
            raise HTTPError(http.client.NOT_FOUND)

    @require_admin
    def post(self, hex_id):
        object_id = bson.objectid.ObjectId(hex_id)
        self.save(object_id)


class LookupFileHandler(BaseRequestHandler, HandlerMixin):
    def get(self, search_term):
        results = self.article_collection.find({
            ArticleCollection.FILE_SHA1: {'$exists': True},
            ArticleCollection.FILENAME: search_term,
        })

        if results.count() == 1:
            result = results[0]
            id_ = bytes_to_b32low_str(result[ArticleCollection.UUID].bytes)
            self.redirect(self.reverse_url(UniqueItemHandler.name, id_))
        elif results.count():
            self.set_status(http.client.MULTIPLE_CHOICES)
            self.render('cms/file_lookup_multiple_choices.html',
                articles=list(results), ArticleCollection=ArticleCollection)
        else:
            raise HTTPError(http.client.NOT_FOUND)


class AllTagsHandler(BaseRequestHandler, HandlerMixin):
    name = 'cms_all_tags'

    def get(self):
        results = list(self.tag_collection.find(
            sort=[(TagCollection.TITLE, pymongo.ASCENDING)]))

        self.render('cms/all_tags.html', TagCollection=TagCollection,
            tags=results,
        )


class TagHandler(BaseRequestHandler, HandlerMixin):
    name = 'cms_tag'

    def get(self, tag_id):
        query = {
            ArticleCollection.TAGS: tag_id,
        }

        if tag_id == 'blog':
            results = list(self.article_collection.find(query,
                sort=[(ArticleCollection.PUBLICATION_DATE, pymongo.DESCENDING)]))
        else:
            results = list(self.article_collection.find(query,
                sort=[(ArticleCollection.TITLE, pymongo.ASCENDING)]))

        if results:
            self.render('cms/all_articles.html', ArticleCollection=ArticleCollection,
                articles=results,
            )
        else:
            raise HTTPError(http.client.NOT_FOUND)


class AllArticlesHandler(BaseRequestHandler, HandlerMixin):
    name = 'cms_all_articles'

    def get(self):
        results = list(self.article_collection.find(
            sort=[(ArticleCollection.TITLE, pymongo.ASCENDING)]))

        self.render('cms/all_articles.html',
            ArticleCollection=ArticleCollection,
            articles=results,
        )


class AtomFeedHandler(BaseRequestHandler, HandlerMixin):
    name = 'cms_atom_feed'

    def get(self):
        results = list(self.article_collection.find(
            {
                '$or': [
                    {ArticleCollection.PRIVATE: False},
                    {ArticleCollection.PRIVATE: {'$exists': False}},
                ]
            },
            sort=[(ArticleCollection.PUBLICATION_DATE, pymongo.DESCENDING)],
            limit=20,
        ))

        if results:
            updated = results[0][ArticleCollection.PUBLICATION_DATE]
        else:
            updated = datetime.datetime.fromtimestamp(0)

        self.set_header('Content-Type', 'application/atom+xml')

        self.render('cms/article_atom.xml', articles=results,
            ArticleCollection=ArticleCollection, updated=updated)


url_specs = (
    URLSpec(r'/a/([0-9a-zA-Z]+)', UniqueItemHandler,
        name=UniqueItemHandler.name),
    URLSpec(r'/a/([0-9a-zA-Z]+);download', DownloadHandler,
         name=DownloadHandler.name),
    URLSpec(r'/a/([0-9a-zA-Z]+);resize=([0-9a-zA-Z]+)', ResizeHandler,
        name=ResizeHandler.name),
    URLSpec(r'/a/file=(.*)', LookupFileHandler,),
    URLSpec(r'/cms/article/new', NewArticleHandler,
        name=NewArticleHandler.name),
    URLSpec(r'/cms/article/edit/([0-9a-f]+)', EditArticleHandler,
        name=EditArticleHandler.name),
    URLSpec(r'/cms/article/delete/([0-9a-f]+)', DeleteArticleHandler,
        name=DeleteArticleHandler.name),
    URLSpec(r'/cms/file/upload', UploadFileHandler,
        name=UploadFileHandler.name),
    URLSpec(r'/cms/file/edit/([0-9a-f]+)', EditFileHandler,
        name=EditFileHandler.name),
    URLSpec(r'/cms/file/lookup/(.+)', LookupFileHandler),
    URLSpec(r'/cms/tags', AllTagsHandler, name=AllTagsHandler.name),
    URLSpec(r'/cms/tag/(.*)', TagHandler, name=TagHandler.name),
    URLSpec(r'/cms/articles', AllArticlesHandler,
        name=AllArticlesHandler.name),
    URLSpec(r'/cms/atom.xml', AtomFeedHandler, name=AtomFeedHandler.name),
)
