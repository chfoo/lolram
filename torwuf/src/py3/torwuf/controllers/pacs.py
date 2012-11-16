'''Pac-Man text art (ascii-pacs)'''
# This file is part of Torwuf.
# Copyright © 2012 Christopher Foo <chris.foo@gmail.com>.
# Licensed under GNU GPLv3. See COPYING.txt for details.
from pywheel.backoff import Trier
from pywheel.db.mongodb import AggregateTagsCode
from tornado.web import HTTPError, URLSpec
from torwuf.controllers.base import (BaseRequestHandler, require_admin,
    tag_list_to_str)
from torwuf.models.pacs import PacsCollection, PacsTagsCollection
import bson
import http.client
import pymongo
import shlex
import string


VALID_TAG_SET = frozenset(string.printable)


class PacsController(object):
    def __init__(self, application):
        self.application = application
        Trier(self._setup_index)

    def _setup_index(self):
        if not self.application.db:
            return False

        self.pac_collection.ensure_index([
            (PacsCollection.TAGS, pymongo.ASCENDING)])

        return True

    @property
    def pac_collection(self):
        return self.application.db[PacsCollection.COLLECTION]

    @property
    def tag_collection(self):
        return self.application.db[PacsTagsCollection.COLLECTION]

    def aggregate_tags(self):
        # XXX: for api 1.9 (2.1.1 out is a required argument)
        self.pac_collection.map_reduce(AggregateTagsCode.make_map_tags_code(),
            AggregateTagsCode.make_reduce_tags_code(),
            out=PacsTagsCollection.COLLECTION)


class ControllerMixin(object):
    @property
    def controller(self):
        return self.application.pacs_controller


class ListAllHandler(BaseRequestHandler, ControllerMixin):
    name = 'pacs_list_all'

    def get(self):
        tag_dict = {}
        tag_results = self.controller.tag_collection.find()

        for result in tag_results:
            tag_dict[result['_id']] = result[PacsTagsCollection.COUNT]

        results = self.controller.pac_collection.find(
            sort=[(PacsCollection.TAGS, 1)])

        self.render('pacs/list_all.html', PacsCollection=PacsCollection,
            results=results, tag_dict=tag_dict)


class NewHandler(BaseRequestHandler, ControllerMixin):
    name = 'pacs_new'

    # FIXME:
#    @require_group('pacs')
    @require_admin
    def get(self):
        self.render('pacs/edit.html', text='', tags='')

#    @require_group('pacs')
    @require_admin
    def post(self):
        text = self.get_argument('text')
        tags = self.get_argument('tags', '')
        tag_list = list(sorted(frozenset(shlex.split(tags))))

        doc_id = self.controller.pac_collection.insert({
            PacsCollection.TEXT: text,
            PacsCollection.TAGS: tag_list
        })

        self.controller.aggregate_tags()

        # FIXME:
#        self.add_message('Pac added')

        self.redirect(self.reverse_url(ListAllHandler.name),
            status=http.client.SEE_OTHER,)
#            api_data={
#                'id': str(doc_id),
#            })


class MassNewHandler(BaseRequestHandler, ControllerMixin):
    name = 'pacs_mass_new'
    SEPERATOR = '{4942fb40-a139-41ba-95a4-c692941e52a9}'

    # FIXME:
#    @require_group('pacs')
    @require_admin
    def get(self):
        self.render('pacs/mass_new.html', mass_text='', tags='',
            seperator=MassNewHandler.SEPERATOR)

#    @require_group('pacs')
    @require_admin
    def post(self):
        mass_text = self.get_argument('mass_text')
        tags = self.get_argument('tags', '')
        tag_list = list(sorted(frozenset(shlex.split(tags))))

        for text in mass_text.split(MassNewHandler.SEPERATOR):
            doc_id = self.controller.pac_collection.insert({
                PacsCollection.TEXT: text,
                PacsCollection.TAGS: tag_list
            })

        self.controller.aggregate_tags()

        # FIXME:
#        self.add_message('lotsa pacs added')

        self.redirect(self.reverse_url(ListAllHandler.name),
            status=http.client.SEE_OTHER)


class ViewSingleHandler(BaseRequestHandler, ControllerMixin):
    name = 'pacs_view_single'

    def get(self, doc_hex_id):
        result = self.controller.pac_collection.find_one(
            bson.objectid.ObjectId(doc_hex_id))

        if result:
            self.render('pacs/view_single.html', result=result,
                PacsCollection=PacsCollection)
        else:
            raise HTTPError(404, 'pac not found')


class EditHandler(BaseRequestHandler, ControllerMixin):
    name = 'pacs_edit'

    # FIXME:
#    @require_group('pacs')
    @require_admin
    def get(self, doc_hex_id):
        result = self.controller.pac_collection.find_one(
            bson.objectid.ObjectId(doc_hex_id))

        if result:
            text = result[PacsCollection.TEXT]
            tags = tag_list_to_str(result[PacsCollection.TAGS])

            self.render('pacs/edit.html', text=text, tags=tags)
        else:
            raise HTTPError(404, 'pac not found')

#    @require_group('pacs')
    @require_admin
    def post(self, doc_hex_id):
        text = self.get_argument('text')
        tags = self.get_argument('tags', '')
        tag_list = list(sorted(frozenset(shlex.split(tags))))

        doc_id = self.controller.pac_collection.save({
            '_id': bson.objectid.ObjectId(doc_hex_id),
            PacsCollection.TEXT: text,
            PacsCollection.TAGS: tag_list
        })

        self.controller.aggregate_tags()

        # FIXME:
#        self.add_message('pac added')

        self.redirect(self.reverse_url(ListAllHandler.name),
            status=http.client.SEE_OTHER)


class ListByTagHandler(BaseRequestHandler, ControllerMixin):
    name = 'pacs_list_by_tag'

    def get(self, tag_name):
        results = self.controller.pac_collection.find({
            PacsCollection.TAGS: tag_name,
        })

        if results.count():
            self.render('pacs/list_by_tag.html', PacsCollection=PacsCollection,
            results=results, tag=tag_name)
        else:
            raise HTTPError(404)


url_specs = (
    URLSpec('/pacs/', ListAllHandler, name=ListAllHandler.name),
    URLSpec('/pacs/new', NewHandler, name=NewHandler.name),
    URLSpec('/pacs/mass_new', MassNewHandler, name=MassNewHandler.name),
    URLSpec('/pacs/tag/(.*)', ListByTagHandler, name=ListByTagHandler.name),
    URLSpec(r'/pacs/([-{}a-zA-Z0-9]+)', ViewSingleHandler,
        name=ViewSingleHandler.name),
    URLSpec(r'/pacs/([-{}a-zA-Z0-9]+)/edit', EditHandler,
        name=EditHandler.name),
)
