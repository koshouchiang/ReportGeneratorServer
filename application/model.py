




class RequestTemplate:

    def __init__(self) -> None:
        pass

    def check_data_completed(self, data : dict) -> bool:
        '''
        check including : report_code and match with algorithm input, and all keys checking
        '''
        
        return True

    def start_process_entrance(self):
        '''
        The entrance in class
        '''
        pass
    
    def prepare_algorithm_input(self) -> tuple:
        '''
        Prepare all things before call algorithms, including data type transfer
        '''
        pass

    def start_algorithm_part(self):
        '''
        before start algorithm part, need to choose algorithm type first
        '''
        pass

    def start_generate_pdf_part(self):
        '''
        before start generate pdf part, need to choose pdf type first
        '''
        pass

    def check_file_endswith(self, kind : str) -> bool:
        '''
        check file endswith return bool
        '''
        pass

    def explode_zip_file(self, file_list : list):
        '''
        file list may one or many, means all of once algorithm need data  
        '''

        pass

    def manual_review(self) -> bool:
        '''
        In the futrue, there have a manual review if flag true means manual review done, can generate pdf 
        '''

        manual_review_done = True
        return manual_review_done
