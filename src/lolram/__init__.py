"""
======
Lolram
======
----------------------------------------------
Python framework and content management system
----------------------------------------------

:author: Christopher Foo
:email: chris.foo@gmail.com

Lolram is a Python framework and content management system. It is a personal
project, and since it is biased toward my needs, I do not recommend using it
for production services. However, feel free to take portions or fork changes
of the code. Just remember the licensing terms.

The current version is in **alpha** state.

Installation
============

Lolram requires

1. Python version 2.6 or greater and strictly less than 3.0 (>2.6 and <<3.0)
2. lxml for HTML generation (python-lxml)
3. SqlAlchemy for database (python-sqlalchemy)
4. flup for WSGI support (python-flup)
5. magic for content management (python-magic)
6. RestructuredText for content text formatting (python-docutils)
7. OpenID for login (python-openid)

and optionally,

8. epydoc for API documentation (python-epydoc)

Architecture
============

Lolram is designed to be run as a WSGI application over a Unix socket. 

Components
----------

Middleware functionality is separated into components. The application can be
thought as one large component.

Components have the following stages:

init
	A singleton instance which other components may interact to start up 
	the application

setup
	Prepare for a request.

control
	This stage is the *controller* portion of the MVC model.

render
	This stage is the *view* portion of the MVC model.

cleanup
	Clean up after the request

Database
--------

SQL database functionality and migration support is
provided through the Database component

Documentation
=============

To generate documentation, please run ``epydoc src/lolram/`` in the source directory.

License and credits
===================

Majority of the code is license under the GNU GPL v3 license.

The 3rd party packages
----------------------

iso8601
~~~~~~~

Copyright 2007 by Michael Twomey. See the package's README file in the package
directory.

urllib3
~~~~~~~

Andrey Petrov. See the source code heading in the package directory.


"""


__docformat__ = 'restructuredtext en'


