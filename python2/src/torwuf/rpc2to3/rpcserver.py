from .openid_ import OpenIDWrapper
import SimpleXMLRPCServer

def make_server(address, port, config_parser):
	openid_wrapper = OpenIDWrapper(config_parser)
	server = SimpleXMLRPCServer.SimpleXMLRPCServer((address, port))
	
	server.register_function(openid_wrapper.openid_stage_1)
	server.register_function(openid_wrapper.openid_stage_2)
	
	return server
	