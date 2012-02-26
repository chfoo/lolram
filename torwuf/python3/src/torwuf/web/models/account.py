'''Account database keys'''
#
#	Copyright (c) 2012 Christopher Foo <chris.foo@gmail.com>
#
#	This file is part of Torwuf.
#
#	Torwuf is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	Torwuf is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with Torwuf.  If not, see <http://www.gnu.org/licenses/>.
#
from torwuf.web.models.base import ModelStringMap

class UsernameCollection(ModelStringMap):
	class Password(ModelStringMap):
		LABEL = 'label'
		PASSWORD = 'password'
	
	COLLECTION = 'usernames'
	USERNAME = 'username'
	DATE_CREATED = 'date_created'
	DATE_DELETED = 'date_deleted'
	ACCOUNT_ID = 'account_id'
	PASSWORDS = 'passwords'


class AccountCollection(ModelStringMap):
	COLLECTION = 'accounts'
	DATE_CREATED = 'date_created'
	DATE_DELETED = 'date_deleted'
	DISPLAY_NAME = 'display_name'
	EMAILS = 'emails'
	UNVERIFIED_EMAILS = 'unverified_emails'
	AUTHORIZED_GROUPS = 'authorized_groups'
	OPENID_ID_URLS = 'openid_id_urls'
	FIRST_NAME = 'first_name'
	LAST_NAME = 'last_name'
