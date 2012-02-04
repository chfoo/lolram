class UsernameCollection(object):
	class Password(object):
		LABEL = 'label'
		PASSWORD = 'password'
	
	COLLECTION = 'usernames'
	USERNAME = 'username'
	DATE_CREATED = 'date_created'
	DATE_DELETED = 'date_deleted'
	ACCOUNT_ID = 'account_id'
	PASSWORDS = 'passwords'


class AccountCollection(object):
	COLLECTION = 'accounts'
	DATE_CREATED = 'date_created'
	DATE_DELETED = 'date_deleted'
	DISPLAY_NAME = 'display_name'
	EMAILS = 'emails'
	UNVERIFIED_EMAILS = 'unverified_emails'
	AUTHORIZED_GROUPS = 'authorized_groups'
	OPENID_ID_URLS = 'openid_id_urls'
