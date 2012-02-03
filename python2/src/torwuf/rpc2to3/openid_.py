import openid.consumer.consumer
import openid.consumer.discover
import openidmongodb
import pickle


class OpenIDWrapper(object):
	def __init__(self, config_parser):
		self.init_association_store(config_parser)
	
	def init_association_store(self, config_parser):
		self.association_store = openidmongodb.MongoDBStore(
			db=config_parser.get('mongodb', 'database'), 
			associations_collection="openid_associations", 
			nonces_collection='openid_nonces', 
			username=config_parser.get('mongodb', 'username'), 
			password=config_parser.get('mongodb', 'password')
		)
		

	def openid_stage_1(self, openid_url, return_to_url, realm):
		session_dict = {}
		
		consumer = openid.consumer.consumer.Consumer(session_dict, self.association_store)
		
		try:
			auth_request = consumer.begin(openid_url)
		except openid.consumer.discover.DiscoveryFailure:
			return False
		else:
			redirect_url = auth_request.redirectURL(realm, return_to=return_to_url)
			session_data = pickle.dumps(session_dict)
			
			return (redirect_url, session_data)

	def openid_stage_2(self, session_data, query_kvp_dict, request_uri):
		session_dict = pickle.loads(session_data)
		consumer = openid.consumer.consumer.Consumer(session_dict, self.association_store)
		response = consumer.complete(query_kvp_dict, request_uri)
			
		if response.status == openid.consumer.consumer.SUCCESS:
			display_identifier = response.getDisplayIdentifier()
			identity_url = response.identity_url
			
			return (identity_url, display_identifier)
		
		else:
			return False