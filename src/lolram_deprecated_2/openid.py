# encoding=utf8

'''OpenID providers'''

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

__docformat__ = 'restructuredtext en'

class OpenIDProvidersInfo(object):
	providers = {
		'google' : ('google.com/accounts/o8/id', 'Google'),
		'yahoo' : ('me.yahoo.com', 'Yahoo!'),
		'microsoft' : ('accountservices.passport.net', 'Windows Live'),
		'livejournal' : ('{{}}.livejournal.com', 'LiveJournal', ),
		'myspace' : ('myspace.com/{{}}', 'MySpace'),
		'wordpress' : ('{{}}.wordpress.com', 'WordPress'),
		'blogger' : ('{{}}.blogger.com', 'Blogger',),
		'verisign' : ('{{}}.pip.verisignlabs.com', 'Verisign'),
		'launchpad' : ('launchpad.net/~{{}}', 'Launchpad'),
		'facebook' : ('facebook.com/{{}}', 'Facebook'),
	}
	emails = {
		'google': ('gmail', 'googlemail'),
		'microsoft': ('hotmail', 'live', 'msn', 'sympatico', 'passport'),
		'yahoo': ('yahoo', 'rogers'),
	}
	
	@classmethod
	def guess_provider_from_email(cls, s):
		for provider, substrings in cls.emails.iteritems():
			for substring in substrings:
				if s.find(substring) != -1:
					return provider
	