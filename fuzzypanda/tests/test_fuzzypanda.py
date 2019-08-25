'''
Tests the fuzzypanda modules

@author: Cody Gilbert
'''
import sys
import unittest
import pandas as pd
import fuzzypanda
import fuzzypanda.matching as fpd
import fuzzypanda.preprocess


class TestPreprocess(unittest.TestCase):
    '''
    Tests the fuzzypanda preprocessing function
    '''
    def setUp(self):
        '''
        Set up the initial testing Pandas DataFrames
        '''
        self.preprocesser = fuzzypanda.preprocess.PreProcessor()

    def test_same_string(self):
        self.assertEqual(self.preprocesser.preprocess('kitten'),
                        'kitten')
        
    def test_remove_default_chars(self):
        self.assertEqual(self.preprocesser.preprocess('!@k#$%^i&*()-t_=+t{}e[]:;\'n\"/|\\?><.,~`'),
                                                      'andkitten')
    
    def test_change_screened_chars(self):
        '''
        Use the screened_chars attribute to keep select characters
        '''
        self.preprocesser.screened_chars = self.preprocesser.screened_chars.replace('&', '')
        self.assertEqual(self.preprocesser.preprocess('!@k#$%^i&*()-t_=+t{}e[]:;\'n\"/|\\?><.,~`'),
                                                      'ki&tten')
        
    def test_change_screened_chars2(self):
        '''
        Use the screened_chars attribute to keep a backslash
        '''
        self.preprocesser.screened_chars = self.preprocesser.screened_chars.replace('\\', '')
        self.assertEqual(self.preprocesser.preprocess('!@k#$%^i*()-t_=+t{}e[]:;\'n\"/|\\?><.,~`'),
                                                      'kitten\\')
    def test_change_screened_chars3(self):
        '''
        Use the screened_chars attribute to only screen &
        '''
        self.preprocesser.screened_chars = '&'
        self.assertEqual(self.preprocesser.preprocess('ki*tt&en'),
                                                      'andenki*tt')
    def test_tokenizer(self):
        '''
        Check the tokenizer transformer
        '''
        self.assertEqual(self.preprocesser.preprocess('sitting kitten'),
                                                      'kittensitting')


class FuzzyTests(unittest.TestCase):
    '''
    Tests the get_fuzzy_columns function, the main fuzzypanda API
    '''
    def setUp(self):
        '''
        Set up the initial testing Pandas DataFrames
        '''
        self.left_df = pd.DataFrame({'ID': ['123314',
                                             '123213',
                                             '43543',
                                             '35435',
                                             '987'],
                                    'sCol': ['kitten',
                                             'siting',
                                             'the times of best',
                                             'the worst times',
                                             'not in there'],
                                    'zCol': ['oboe',
                                             'trvmpet',
                                             'over te rainbow',
                                             'in Symphony C',
                                             'not in there']})
        self.right_df = pd.DataFrame({'ID': ['12783314',
                                             '12352213',
                                             '43233543',
                                             '23432420'],
                                    'RsCol': ['kitten',
                                              'sitting',
                                              'the best of times',
                                              'the worst of times'],
                                    'RzCol': ['oboe',
                                              'trumpet',
                                              'over the rainbow',
                                              'Symphony in C#']})
        
    def test_get_fuzzy_columns(self):
        '''
        Test the basic functionality of get_fuzzy_columns
        '''
        left_fuzzy_df = pd.DataFrame({'ID': ['123314',
                                             '123213',
                                             '43543',
                                             '35435',
                                             '987'],
                                        'sCol': ['kitten',
                                             'siting',
                                             'the times of best',
                                             'the worst times',
                                             'not in there'],
                                        'zCol': ['oboe',
                                             'trvmpet',
                                             'over te rainbow',
                                             'in Symphony C',
                                             'not in there'],
                                        'fuzzy_sCol': ['kitten',
                                                       'sitting',
                                                       'the best of times',
                                                       'the worst of times',
                                                       'not in there']}) 

        fpd.get_fuzzy_columns(self.left_df,
                              self.right_df,
                              left_cols=['sCol'],
                              right_cols=['RsCol'])
        self.assertTrue(self.left_df.equals(left_fuzzy_df))
        
    def test_null_return(self):
        '''
        Test the get_fuzzy_columns null_return='NULL' argument
        '''
        left_fuzzy_df = pd.DataFrame({'ID': ['123314',
                                             '123213',
                                             '43543',
                                             '35435',
                                             '987'],
                                    'sCol': ['kitten',
                                             'siting',
                                             'the times of best',
                                             'the worst times',
                                             'not in there'],
                                    'zCol': ['oboe',
                                             'trvmpet',
                                             'over te rainbow',
                                             'in Symphony C',
                                             'not in there'],
                                    'fuzzy_sCol': ['kitten',
                                                   'sitting',
                                                   'the best of times',
                                                   'the worst of times',
                                                   'NULL']})
        fpd.get_fuzzy_columns(self.left_df,
                              self.right_df,
                              left_cols=['sCol'],
                              right_cols=['RsCol'],
                              null_return='NULL')
        self.assertTrue(self.left_df.equals(left_fuzzy_df))
        
    def test_multiple_columns(self):
        '''
        Test multiple columns
        '''
        left_fuzzy_df = pd.DataFrame({'ID': ['123314',
                                             '123213',
                                             '43543',
                                             '35435',
                                             '987'],
                                      'sCol': ['kitten',
                                               'siting',
                                               'the times of best',
                                               'the worst times',
                                               'not in there'],
                                      'zCol': ['oboe',
                                               'trvmpet',
                                               'over te rainbow',
                                               'in Symphony C',
                                               'not in there'],
                                      'fuzzy_sCol': ['kitten',
                                                     'sitting',
                                                     'the best of times',
                                                     'the worst of times',
                                                     'not in there'],
                                      'fuzzy_zCol': ['oboe',
                                                     'trumpet',
                                                     'over the rainbow',
                                                     'Symphony in C#',
                                                     'not in there']})
        fpd.get_fuzzy_columns(self.left_df,
                              self.right_df,
                              left_cols=['sCol', 'zCol'],
                              right_cols=['RsCol', 'RzCol'])
        self.assertTrue(self.left_df.equals(left_fuzzy_df))

    def test_no_right_cols(self):
        '''
        Test no right_cols input
        '''
        self.left_df.columns = ['ID', 'col_1', 'col_2']
        self.right_df.columns = ['ID', 'col_1', 'col_2']
        left_fuzzy_df = pd.DataFrame({'ID': ['123314',
                                             '123213',
                                             '43543',
                                             '35435',
                                             '987'],
                                      'col_1': ['kitten',
                                               'siting',
                                               'the times of best',
                                               'the worst times',
                                               'not in there'],
                                      'col_2': ['oboe',
                                               'trvmpet',
                                               'over te rainbow',
                                               'in Symphony C',
                                               'not in there'],
                                      'fuzzy_col_1': ['kitten',
                                                     'sitting',
                                                     'the best of times',
                                                     'the worst of times',
                                                     'not in there'],
                                      'fuzzy_col_2': ['oboe',
                                                     'trumpet',
                                                     'over the rainbow',
                                                     'Symphony in C#',
                                                     'not in there']})
        fpd.get_fuzzy_columns(self.left_df,
                              self.right_df,
                              left_cols=['col_1', 'col_2'])
        self.assertTrue(self.left_df.equals(left_fuzzy_df))

        
if __name__ == "__main__":
    sys.argv = ['','-v']
    unittest.main()