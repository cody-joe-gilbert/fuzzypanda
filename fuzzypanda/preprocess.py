'''
@author: Cody Gilbert

This module contains the builtin string preprocesser used in the fuzzypandas
fuzzy lookup module

Classes:
    PreProcessor: carries the 'preprocess' method used for fuzzypandas string
        pre-processing.

'''

class PreProcessor():
    '''
    This pre-built class performs a basic level of string preprocessing using
    a few heuristics of string lookups. If you wish to create a different set
    of pre-processing criteria you may create a custom copy of this class
    and pass a pre-built custom PreProcessor object to 
    fuzzypanda.get_fuzzy_columns.
    
    Attributes:
        screened_chars: contains a string of characters that will be removed 
            from all strings. By default this will be:
            !@#$%^&*()-_=+{}[]:;'"/|\?><.,~`
            The characters that are screened can be changed by resetting this
            attribute after object instantiation.
    Methods:
        preprocess: function to preprocess the strings. Performs the following
            transformations:
                1. Letters converted to all lowercase 
                2. Special characters selected or default
                    characters not kept are removed
                    (replaced with ''). 
                    The special character '&' will be replaced with ' and '
                3. String is split over whitespace (with left-right stripping),
                     resulting list is lexigraphically sorted, and the
                     list is joined without spaces.
                     WARNING: Symspell will split strings by whitespace, and 
                         will not consider matching strings that contain space.
                         If this preprocessing function is modified, ensure that
                         whitespace is still eliminated.
    
    '''
    def __init__(self):
        self.screened_chars = '!@#$%^&*()-_=+{}[]:;\'\"/|\\?><.,~`'
        

    def preprocess(self, s):
        '''
        Pre-processes the input string to apply basic string-matching
        heuristics. See Returns for operations. The final string
        will be a common sequence of characters that can be used
        for string comparisons.
        
        Args:
            s: input string to be transformed
            
        Returns:
            t: transformed string undergoing the following:
                
        '''
        # 1. Set all characters to lowercase
        # WARNING: Symspell automatically searches for characters that are
        #    cast to lowercase. Changing the preprocessing case WILL break
        #    the fuzzy search algorithm 
        t = s.lower()
        # 2. Replace all the screened characters 
        for c in self.screened_chars:
            if c == '&':
                t = t.replace(c, ' and ')
            else:
                t = t.replace(c, '')
        # 3. Split over spaces, lexical sort, and re-cat
        tl = t.split()
        tl.sort()
        t = ''.join(tl)
        return(t)
