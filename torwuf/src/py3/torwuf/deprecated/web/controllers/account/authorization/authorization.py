'''Authorization controller'''
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
from tornado.web import HTTPError
from torwuf.deprecated.web.controllers.account.authorization.decorators \
    import require_admin
from torwuf.deprecated.web.controllers.base import BaseController
from torwuf.deprecated.web.models.account import AccountCollection
import http
import torwuf.deprecated.web.controllers.base
import uuid


class AuthorizationController(BaseController):
    def init(self):
        self.add_url_spec('/account/groups/add/([-a-z0-9]+)', AddGroupHandler)

    def is_admin_account(self, account_id):
        admin_email = self.config.config_parser['application']['admin-email']

        result = self.application.database[AccountCollection.COLLECTION].\
            find_one({
            '_id': account_id,
            AccountCollection.EMAILS: admin_email,
        })

        return True if result else False

    def is_account_in_group(self, account_id, *group):
        result = self.application.database[AccountCollection.COLLECTION].\
            find_one({
            '_id': account_id,
            AccountCollection.AUTHORIZED_GROUPS: group,
        })

        return True if result else False


class AddGroupHandler(torwuf.deprecated.web.controllers.base.BaseHandler):
    name = 'authorization_account_groups'

    @require_admin
    def get(self, account_uuid_str):
        uuid_obj = uuid.UUID(account_uuid_str)

        result = self.controller.application.database[
            AccountCollection.COLLECTION].find_one({
                '_id': uuid_obj,
        })

        self.render('authorization/account_groups_add.html',
            display_name=result[AccountCollection.DISPLAY_NAME]
        )

    @require_admin
    def post(self, account_uuid_str):
        group_name = self.get_argument('group')

        if len(group_name) > 12:
            raise HTTPError(http.client.BAD_REQUEST, 'Group name too long')

        uuid_obj = uuid.UUID(account_uuid_str)

        result = self.controller.application.database[
            AccountCollection.COLLECTION].find_one({
                '_id': uuid_obj,
        })

        groups = set(result.get(AccountCollection.AUTHORIZED_GROUPS, []))
        groups.add(group_name)

        self.controller.application.database[AccountCollection.COLLECTION].\
            update(
            {'_id': uuid_obj},
            {'$set':
                {AccountCollection.AUTHORIZED_GROUPS: list(groups)}
            }
        )

        self.redirect(self.reverse_url('account_profile'))
