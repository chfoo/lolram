'''The python 2 rpc server'''
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
from .openid_ import OpenIDWrapper
import SimpleXMLRPCServer

def make_server(address, port, config_parser):
	openid_wrapper = OpenIDWrapper(config_parser)
	server = SimpleXMLRPCServer.SimpleXMLRPCServer((address, port))
	
	server.register_function(openid_wrapper.openid_stage_1)
	server.register_function(openid_wrapper.openid_stage_2)
	
	return server
	