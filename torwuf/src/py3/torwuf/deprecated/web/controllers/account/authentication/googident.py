'''Google Identity Toolkit controller'''
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
from .mixins import ProcessingMixIn
from tornado.web import HTTPError
from torwuf.deprecated.web.controllers.base import BaseController, BaseHandler
from torwuf.deprecated.web.models.authentication import (SuccessSessionKeys,
    SessionKeys)
import http.client
import json
import logging
import threading
import urllib.parse

_logger = logging.getLogger(__name__)

# https://code.google.com/apis/identitytoolkit/v1/reference.html


class GoogleIdentityController(BaseController):
    def init(self):
        self.add_url_spec('/googident/login', LoginHandler)
        self.add_url_spec('/googident/login/domain/([a-z]+)', DomainHandler)
        self.add_url_spec('/googident/login/return', ReturnHandler)
        self.add_url_spec('/googident/not_supported', NotSupportedHandler)
        self.init_connection_pool()

    @property
    def api_key(self):
        return self.config.config_parser['googleapi']['server-key']

    def init_connection_pool(self):
        self.connection = http.client.HTTPSConnection('www.googleapis.com')
        self.lock = threading.Lock()

    def make_connection(self, path, body=None):
        # TODO: is http.client thread safe? should be using a lock?

        with self.lock:
            for attempt_number in range(2):
                try:
                    _logger.debug('Making request to googleapis=%s', path)
                    self.connection.request('POST', path, body,
                        headers={'Content-Type': 'application/json'})

                    break
                except http.client.NotConnected:
                    _logger.debug('Not Connected')
                    self.connection.connect()
                except http.client.ImproperConnectionState:
                    _logger.debug('Bad connection state')
                    self.connection.close()
                    self.connection.connect()
                except http.client.BadStatusLine:
                    _logger.debug('Bad status line')
                    self.connection.close()
                    self.connection.connect()
            else:
                raise Exception('unable to make a new connection')

        return self.connection

    def create_auth_url(self, continue_url, identifier, remote_ip, realm):
        path = '/identitytoolkit/v1/relyingparty/createAuthUrl?' + \
            urllib.parse.urlencode(dict(
                key=self.api_key,
                userIp=remote_ip,
            ))
        body = json.dumps(dict(
            continueUrl=continue_url,
            identifier=identifier,
            openidRealm=realm,
        ))

        print(continue_url)

        response = self.make_connection(path, body).getresponse()
        response_str = str(response.read(), 'utf8')

        if response.status == 200:
            data = json.loads(response_str)
            return data['authUri']

        _logger.debug('Failed google identity toolkit create auth url ' + \
            'status=%s reason=%s',
            response.status, response_str)

    def verify_assertation(self, request_uri, post_body, remote_ip):
        path = '/identitytoolkit/v1/relyingparty/verifyAssertion?' + \
            urllib.parse.urlencode(dict(
                key=self.api_key,
                userIp=remote_ip,
            ))
        body = json.dumps(dict(
            requestUri=request_uri,
            postBody=post_body
        ))

        response = self.make_connection(path, body).getresponse()
        response_str = str(response.read(), 'utf8')

        if response.status == 200:
            data = json.loads(response_str)
            return data


class HandlerMixIn(ProcessingMixIn):
    def get_return_to_url(self):
        return self.request.protocol + '://' + self.request.host + \
            self.reverse_url('googident_login_return')


class LoginHandler(BaseHandler, HandlerMixIn):
    name = 'googident_login'

    def get(self):
        self.render('authentication/googident/login.html')

    def post(self):
        url = self.controller.create_auth_url(self.get_return_to_url(),
            self.get_argument('email'), self.request.remote_ip,
            self.get_openid_realm())

        if url:
            self.redirect(url)
        else:
            self.redirect(self.reverse_url('googident_not_supported'))


class DomainHandler(BaseHandler, HandlerMixIn):
    name = 'googident_login_domain'

    # Map created by trial and error
    domain_identifier_map = {
        'gmail': 'https://gmail.com',
        'aol': 'http://aol.com',
        'yahoo': 'http://yahoo.com',
    }

    def get(self, domain):
        identifier = DomainHandler.domain_identifier_map.get(domain)

        if not identifier:
            raise HTTPError(400)

        url = self.controller.create_auth_url(self.get_return_to_url(),
            identifier, self.request.remote_ip, self.get_openid_realm())

        if url:
            self.redirect(url)
        else:
            raise HTTPError(500)


class ReturnHandler(BaseHandler, HandlerMixIn):
    name = 'googident_login_return'

    def get(self):
        return self.post()

    def post(self):
        data = self.controller.verify_assertation(self.request.full_url(),
            self.request.body, self.request.remote_ip)

        if data:
            display_name = data.get('displayName') or data.get('firstName') \
                or data['verifiedEmail'].split('@', 1)[0]

            self.session[SuccessSessionKeys.KEY] = {
                SuccessSessionKeys.DISPLAY_NAME: display_name,
                SuccessSessionKeys.EMAIL: data.get('verifiedEmail'),
                SuccessSessionKeys.OPENID: data.get('identifier'),
                SuccessSessionKeys.FIRST_NAME: data.get('firstName'),
                SuccessSessionKeys.LAST_NAME: data.get('lastName'),
            }
            self.session[SessionKeys.CURRENT_OPENID] = data['identifier']
            self.session_commit()
            self.redirect(self.reverse_url('account_openid_success'))
        else:
            self.redirect(self.reverse_url('googident_not_supported'))


class NotSupportedHandler(BaseHandler):
    name = 'googident_not_supported'

    def get(self):
        self.render('authentication/googident/not_supported.html')
