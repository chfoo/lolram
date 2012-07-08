'''Enhancements for Tornado Web'''
#
#    Copyright © 2012 Christopher Foo <chris.foo@gmail.com>
#
#    This file is part of Lolram.
#
#    Lolram is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Lolram is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Lolram.  If not, see <http://www.gnu.org/licenses/>.
#

__docformat__ = 'restructuredtext en'


class RequestHandlerMixin(object):
    @property
    def controllers(self):
        """An alias for `self.application.controllers`."""
        return self.application.controllers


class ApplicationMixin(object):
    def __init__(self,):
        self.controllers = {}

    def add_controller(self, *controller_classes):
        handlers = []

        for controller_class in controller_classes:
            controller = controller_class(self)
            self.controllers[controller_class] = controller
            handlers.extend(controller.get_handlers())

        self.add_handlers(".*$", handlers)


class Controller(object):
    """An instance-wide controller class

    Use this class to provide modularity of handlers. Pass a list of
    `Controller`s to the application's constructor.
    """

    def __init__(self, application):
        self.application = application
        self.init()

    def get_handlers(self):
        """To be overridden to provide handlers to the application"""

        raise NotImplementedError()

    def init(self):
        '''Override this class for initalization routines'''
        pass
