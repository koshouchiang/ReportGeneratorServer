import unittest
import json
from testing.globals import app
from testing.func import mock_access_token


class BaseTestCase(unittest.TestCase):
    """Base Test Case which providing 'setUp' and 'assert_result' method."""

    def setUp(self):
        """Hook method for setting up the test fixture before exercising it."""
        # use flask test client to send a request.
        self.app = app
        self.client = app.test_client()




    def tearDown(self):
        """Hook method for deconstructing the test fixture after testing it."""

        pass


    def post_request(self, endpoint: str, data: dict, access_token: str = None):
        """
        sending a post request to test client with access token in json content.
        """
        
        # send request to test client.
        json_object = json.dumps(data)
        with self.app.app_context():
            # if not access_token:
            #     access_token = mock_access_token()
            response = self.client.post(endpoint,
                                        data=json_object,
                                        content_type='application/json',
                                        headers={'Authorization' : 'Bearer {}'.format(access_token)})
        return response

    def post_request_without_token(self, endpoint: str, data: dict):
        """
        sending a post request to test client without access token in json content.
        """
        # send request to test client.
        json_object = json.dumps(data)
        with self.app.app_context():
            response = self.client.post(endpoint,
                                        data=json_object,
                                        content_type='application/json')

        return response

    def get_request(self, endpoint: str, access_token: str = None):
        """
        sending a get request to test client with access token in json content.
        """
        # send request to test client.
        with self.app.app_context():
            # if not access_token:
            #     access_token = mock_access_token()
            response = self.client.get(endpoint,
                                       content_type='application/json',
                                       headers={'Authorization' : 'Bearer {}'.format(access_token)})

        return response


    def assert_result(self, response, result: dict, http_status_code: int = 200, data_status_code: int = 0):
        """
        Assert:
            Response.status_code = 200
            Dictionary of Response.data:
                StatusCode = 0
                key value of Data items equal to the result.
        """
        # assert http status code.
        self.assertEqual(http_status_code, response.status_code)

        # if result is not dict, try to get __dict__.
        if not isinstance(result, dict):
            result = result.__dict__

        resp_obj = json.loads(response.data)

        # assert status code.
        resp_code = resp_obj.get("StatusCode")
        self.assertEqual(resp_code, data_status_code)

        # assert data.
        resp_dict = resp_obj.get("Data")
        if isinstance(resp_dict, list):
            resp_dict = resp_dict[0]

        for key, value in result.items():
            # assert key.
            self.assertIn(key, resp_dict)

            # assert value.
            resp_value = resp_dict.get(key)
            self.assertEqual(resp_value, value)

    def assert_true(self, response, http_status_code: int = 200, data_status_code: int = 0):
        """
        Assert:
            Response.status_code = 200
            Dictionary of Response.data:
                StatusCode = 0
                Data = True.
        """
        # assert http status code.
        self.assertEqual(http_status_code, response.status_code)

        resp_obj = json.loads(response.data)

        # assert status code.
        resp_code = resp_obj.get("StatusCode")
        self.assertEqual(resp_code, data_status_code)

        # assert data.
        resp_result = resp_obj.get("Data")
        self.assertEqual(resp_result, True)

    def assert_null(self, response, http_status_code: int = 200, data_status_code: int = 0):
        """
        Assert:
            Response.status_code = 200
            Dictionary of Response.data:
                StatusCode = 0
                Data = None.
        """
        # assert http status code.
        self.assertEqual(http_status_code, response.status_code)

        resp_obj = json.loads(response.data)

        # assert status code.
        resp_code = resp_obj.get("StatusCode")
        self.assertEqual(resp_code, data_status_code)

        # assert data.
        resp_result = resp_obj.get("Data")
        self.assertEqual(resp_result, None)

    def assert_ok(self, response, http_status_code: int = 200, data_status_code: int = 0):
        """
        Assert:
            Response.status_code = 200
            Dictionary of Response.data:
                StatusCode = 0
        """
        # assert http status code.
        self.assertEqual(http_status_code, response.status_code)

