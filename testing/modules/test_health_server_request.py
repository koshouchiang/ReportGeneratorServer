from testing.base import BaseTestCase
from testing.func import mock_access_token

token = mock_access_token()


class Aclass(BaseTestCase):

    def post_create_success(self):
        '''
        success
        '''

        data = { "report_code" : "S001V1", "user_id" : 7, "health_server_got_generate_request_time": 1660094681353, "health_server_post_create_time": 1664265075021, "user_info": { "id": "7", "name": "koshou", "email": "koshou@singularwings.com", "gender": "男", "height": "176", "weight": "90", "birthday": "1996/10/10", "age": "25" }, "algorithm_input": { "step_test_start_tt" : 1662111836963, "step_test_end_tt" : 1662112234177, "exercise_start_tt" : 1662112291507, "exercise_end_tt" : 1662114091512, "user_info": { "id": "7", "name": "koshou", "email": "koshou@singularwings.com", "gender": "男", "height": "176", "weight": "90", "birthday": "1996/10/10", "age": "25" } } }
        response = self.post_request(endpoint = '/report/generate/create', data = data, access_token = token)
        return response

    def post_create_no_token(self):
        '''
        no token
        '''

        pass

    def post_create_data_uncompleted(self):
        '''
        data uncompleted
        '''
        pass


    def test_post_create_success(self):
        response = self.post_create_success()
        self.assert_ok(response)

        
