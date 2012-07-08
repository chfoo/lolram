'''User account management controller'''
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
from tornado.httpclient import HTTPError
from torwuf.deprecated.web.controllers.account.authentication.decorators \
    import require_authentication
from torwuf.deprecated.web.controllers.account.authorization.decorators \
    import require_admin
from torwuf.deprecated.web.models.account import AccountCollection
from torwuf.deprecated.web.models.authentication import SuccessSessionKeys
import datetime
import string
import torwuf.deprecated.web.controllers.base
import uuid

VALID_USERNAME_SET = frozenset(string.ascii_lowercase) \
    | frozenset(string.digits)


def validate_username_chars(username):
    return frozenset(username) <= VALID_USERNAME_SET


def normalize_username(username):
    username = username.lower().strip('._-')

    if validate_username_chars(username):
        return username


class AccountController(torwuf.deprecated.web.controllers.base.BaseController):
    def init(self):
        self.add_url_spec('/account/', DefaultHandler)
        self.add_url_spec('/account/openid_success', OpenIDSuccessHandler)
        self.add_url_spec('/account/login', LoginHandler)
        self.add_url_spec('/account/logout', LogoutHandler)
        self.add_url_spec('/account/openid_success/new_federated_account',
            NewFederatedAccountHandler)
        self.add_url_spec('/account/profile', ProfileHandler)
        self.add_url_spec('/account/post_login', PostLoginHandler)
        self.add_url_spec('/account/profile/edit', EditProfileHandler)
        self.add_url_spec('/account/list_all', ListAllHandler)
#        self.add_url_spec('/account/passwords', PasswordsHandler)
#        self.add_url_spec('/account/passwords/add', AddPasswordHandler)
#        self.add_url_spec('/account/passwords/delete', DeletePasswordHandler)

    def init_collection(self):
        self.database[AccountCollection.COLLECTION].ensure_index(
            AccountCollection.EMAILS)
        self.database[AccountCollection.COLLECTION].ensure_index(
            AccountCollection.OPENID_ID_URLS)


class HandlerMixIn(object):
    @property
    def account_collection(self):
        return self.app_controller.database[AccountCollection.COLLECTION]


class DefaultHandler(torwuf.deprecated.web.controllers.base.BaseHandler):
    def get(self):
        self.redirect('/account/profile')


class LoginHandler(torwuf.deprecated.web.controllers.base.BaseHandler):
    def get(self):
        if self.current_user and self.current_user.startswith('account'):
            # TODO: reverse_url
            self.redirect('/account/')
        else:
            self.redirect('/googident/login')


class LogoutHandler(torwuf.deprecated.web.controllers.base.BaseHandler):
    name = 'account_logout'

    def get(self):
        self.logout()
        self.session_commit()

        self.render('account/logout_success.html')


class ProfileHandler(torwuf.deprecated.web.controllers.base.BaseHandler,
HandlerMixIn):
    name = 'account_profile'

    @require_authentication
    def get(self):
        result = self.account_collection.find_one(
            {'_id': self.current_account_uuid})

        self.render('account/profile.html',
            AccountCollection=AccountCollection,
            db_model=result)


class EditProfileHandler(torwuf.deprecated.web.controllers.base.BaseHandler,
HandlerMixIn):
    name = 'account_profile_edit'

    @require_authentication
    def get(self):
        result = self.account_collection.find_one(
            {'_id': self.current_account_uuid})

        self.render('account/edit_profile.html',
            display_name=result[AccountCollection.DISPLAY_NAME])

    @require_authentication
    def post(self):
        display_name = self.get_argument('display_name')

        self.account_collection.update({'_id': self.current_account_uuid},
            {'$set': {AccountCollection.DISPLAY_NAME: display_name}})

        self.redirect(self.reverse_url(ProfileHandler.name))


class NewFederatedAccountHandler(torwuf.deprecated.web.controllers.base.\
BaseHandler, HandlerMixIn):
    name = 'account_new_federated_account'

    def get(self):
        session_data = self.session[SuccessSessionKeys.KEY]

        render_dict = dict(
            first_name=session_data[SuccessSessionKeys.FIRST_NAME],
            last_name=session_data[SuccessSessionKeys.LAST_NAME],
            display_name=session_data[SuccessSessionKeys.DISPLAY_NAME],
            email=session_data[SuccessSessionKeys.EMAIL],
        )

        self.render('account/new_federated_account.html', **render_dict)

    def post(self):
        session_data = self.session.get(SuccessSessionKeys.KEY)

        result = self.account_collection.find_one({
            AccountCollection.OPENID_ID_URLS: session_data[
                SuccessSessionKeys.OPENID],
            AccountCollection.EMAILS: session_data[SuccessSessionKeys.EMAIL],
        })

        if result:
            self.redirect(self.reverse_url(OpenIDSuccessHandler.name))
            return

        account_id = uuid.uuid4()

        self.account_collection.insert({
            '_id': account_id,
            AccountCollection.EMAILS: [session_data[SuccessSessionKeys.EMAIL]],
            AccountCollection.DATE_CREATED: datetime.datetime.utcnow(),
            AccountCollection.DISPLAY_NAME: session_data[
                SuccessSessionKeys.DISPLAY_NAME],
            AccountCollection.FIRST_NAME: session_data[
                SuccessSessionKeys.FIRST_NAME],
            AccountCollection.LAST_NAME: session_data[
                SuccessSessionKeys.LAST_NAME],
            AccountCollection.OPENID_ID_URLS: [session_data[
                SuccessSessionKeys.OPENID]],
        })

        self.current_account_id = account_id.bytes
        self.session_commit()
        self.redirect(self.reverse_url(PostLoginHandler.name))


class OpenIDSuccessHandler(torwuf.deprecated.web.controllers.base.BaseHandler,
HandlerMixIn):
    name = 'account_openid_success'

    def get(self):
        session_data = self.session.get(SuccessSessionKeys.KEY)

        if not session_data:
            # TODO: redirect to user-friendly error page
            raise HTTPError(400)

        # NOTE: This algorithm tries to be greedy as possible. It handles
        # the case where the realm is different (http vs https)
        # It is vulnerable to expired email attacks.
        # It is vulnerable to providers returning a different email than the
        # initial provided email
        # TODO: Check for expired/old accounts to avoid expired email attacks

        results = self.account_collection.find({
            '$or': [
                {AccountCollection.OPENID_ID_URLS: session_data[
                    SuccessSessionKeys.OPENID]},
                {AccountCollection.EMAILS: session_data[
                    SuccessSessionKeys.EMAIL]},
            ],
        })

        if results.count() == 1:
            self.current_account_id = results[0]['_id'].bytes
            self.session_commit()
            self.redirect(self.reverse_url(PostLoginHandler.name))
        elif results.count() == 0:
            self.redirect(self.reverse_url(NewFederatedAccountHandler.name))
        else:
            self.redirect(self.reverse_url(SwitchAccountHandler.name))


class SwitchAccountHandler(torwuf.deprecated.web.controllers.base.BaseHandler,
HandlerMixIn):
    name = 'account_switch_account'

    # TODO: handle this case
#    def get(self, account_id=None):
#        pass
#    self.render('account/multiple_account_select.html',
#                db_models=results, AccountCollection=AccountCollection)


class PostLoginHandler(torwuf.deprecated.web.controllers.base.BaseHandler):
    name = 'account_post_login'

    def get(self):
        # TODO: determine whether login is persistent
        # TODO: redirect user to where they wanted to go originally
        self.redirect('/')


class ListAllHandler(torwuf.deprecated.web.controllers.base.BaseHandler,
HandlerMixIn):
    name = 'account_list_all'

    @require_admin
    def get(self):
        results = self.account_collection.find()

        self.render('account/list_all.html',
            AccountCollection=AccountCollection,
            results=results)
