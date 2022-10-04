from testing.base import BaseTestCase
from testing.func import mock_access_token

token = mock_access_token()


class HealthServerRequestTestCase(BaseTestCase):

    def post_create_success(self):
        '''
        success
        '''

        data = { "report_code" : "S001V1", "user_id" : 7, "health_server_got_generate_request_time": 1660094681353, "health_server_post_create_time": 1664265075021, "user_info": { "id": "7", "name": "koshou", "email": "koshou@singularwings.com", "gender": "男", "height": "176", "weight": "90", "birthday": "1996/10/10", "age": "25" }, "algorithm_input": { "step_test_start_tt" : 1662111836963, "step_test_end_tt" : 1662112234177, "exercise_start_tt" : 1662112291507, "exercise_end_tt" : 1662114091512, "user_info": { "id": "7", "name": "koshou", "email": "koshou@singularwings.com", "gender": "男", "height": "176", "weight": "90", "birthday": "1996/10/10", "age": "25" } } }
        response = self.post_request(endpoint = '/report/generate/create', data = data, access_token = token)
        return response

    def post_create_token_error(self):
        '''
        token error
        '''

        data = { "report_code" : "S001V1", "user_id" : 7, "health_server_got_generate_request_time": 1660094681353, "health_server_post_create_time": 1664265075021, "user_info": { "id": "7", "name": "koshou", "email": "koshou@singularwings.com", "gender": "男", "height": "176", "weight": "90", "birthday": "1996/10/10", "age": "25" }, "algorithm_input": { "step_test_start_tt" : 1662111836963, "step_test_end_tt" : 1662112234177, "exercise_start_tt" : 1662112291507, "exercise_end_tt" : 1662114091512, "user_info": { "id": "7", "name": "koshou", "email": "koshou@singularwings.com", "gender": "男", "height": "176", "weight": "90", "birthday": "1996/10/10", "age": "25" } } }
        response = self.post_request(endpoint = '/report/generate/create', data = data)
        return response

    def post_create_data_uncompleted(self):
        '''
        data uncompleted
        '''

        data = { "user_id" : 7, "health_server_got_generate_request_time": 1660094681353, "health_server_post_create_time": 1664265075021, "user_info": { "id": "7", "name": "koshou", "email": "koshou@singularwings.com", "gender": "男", "height": "176", "weight": "90", "birthday": "1996/10/10", "age": "25" }, "algorithm_input": { "step_test_start_tt" : 1662111836963, "step_test_end_tt" : 1662112234177, "exercise_start_tt" : 1662112291507, "exercise_end_tt" : 1662114091512, "user_info": { "id": "7", "name": "koshou", "email": "koshou@singularwings.com", "gender": "男", "height": "176", "weight": "90", "birthday": "1996/10/10", "age": "25" } } }
        response = self.post_request(endpoint = '/report/generate/create', data = data, access_token = token)
        return response


    def get_query_success(self):
        '''
        success
        '''

        response = self.get_request(endpoint = '/report/generate/query/1', access_token = token)
        return response

    def get_query_token_error(self):
        '''
        token error
        '''
        
        response = self.get_request(endpoint = '/report/generate/query/1')
        return response

    def get_query_report_table_index_error(self):
        '''
        no report_table_index
        '''
        
        response = self.get_request(endpoint = '/report/generate/query/9999', access_token = token)
        return response

    def get_query_no_result_message(self):
        '''
        no result_message
        '''
        
        response = self.get_request(endpoint = '/report/generate/query/2', access_token = token)
        return response

    def get_query_algorithm_fail(self):
        '''
        no result_message
        '''
        
        response = self.get_request(endpoint = '/report/generate/query/3', access_token = token)
        return response

    def get_pdf_token_error(self):
        '''
        token error
        '''
        
        response = self.get_request(endpoint = '/report/generate/pdf/1')
        return response

    def get_pdf_no_table_index(self):
        '''
        no report_table_index
        '''
        
        response = self.get_request(endpoint = '/report/generate/pdf/9999', access_token = token)
        return response

    def get_pdf_not_done(self):
        '''
        pdf not done
        '''
        
        response = self.get_request(endpoint = '/report/generate/pdf/3', access_token = token)
        return response

    def test_post_create_success(self):
        response = self.post_create_success()
        self.assert_ok(response)

    def test_post_create_no_token(self):
        response = self.post_create_token_error()
        self.assert_ok(response, http_status_code = 401)
        
    def test_post_create_no_token(self):
        response = self.post_create_data_uncompleted()
        self.assert_ok(response, http_status_code = 402)
        
    def test_get_query_success(self):
        response = self.get_query_success()
        self.assert_ok(response, http_status_code = 200)

    def test_get_query_token_error(self):
        response = self.get_query_token_error()
        self.assert_ok(response, http_status_code = 401)

    def test_get_query_report_table_index_error(self):
        response = self.get_query_report_table_index_error()
        self.assert_ok(response, http_status_code = 402)

    def test_get_query_no_result_message(self):
        response = self.get_query_no_result_message()
        self.assert_ok(response, http_status_code = 403)

    def test_get_query_algorithm_fail(self):
        response = self.get_query_algorithm_fail()
        self.assert_ok(response, http_status_code = 405)
        
    def test_get_pdf_token_error(self):
        response = self.get_pdf_token_error()
        self.assert_ok(response, http_status_code = 401)

    def test_get_pdf_not_done(self):
        response = self.get_pdf_no_table_index()
        self.assert_ok(response, http_status_code = 402)
        
    def test_get_pdf_not_done(self):
        response = self.get_pdf_not_done()
        self.assert_ok(response, http_status_code = 403)
        

        