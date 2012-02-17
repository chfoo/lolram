
import torwuf.tests.web.server_base
import unittest


class TestIndex(unittest.TestCase, torwuf.tests.web.server_base.ServerBaseMixIn):
	def __init__(self, *args):
		unittest.TestCase.__init__(self, *args)
		self.create_app()
		self.start_server()

	def test_basic(self):
		response = self.request('/')
		
		self.assertEqual(response.status, 200)


if __name__ == "__main__":
	#import sys;sys.argv = ['', 'Test.testName']
	unittest.main()