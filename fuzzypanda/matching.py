'''
@author: Cody Gilbert

This module contains tools for creating columns for fuzzy joining two Pandas
DataFrames. The primary API is the get_fuzzy_columns function that takes two
Pandas DataFrames and a set of column names, and creates a new column in the
left DataFrame that contains the closest entries by string edit distance
to the associated values in the right DataFrame columns.

This module uses the Symspell Python port by mammothb of the original C# 
implementation of Symspell by Wolf Garbe. This fuzzy column creation approach
applies a Pandas-friendly wrapper around the Symspell Symmetric Delete spelling 
correction algorithm to allow substantially faster fuzzy joining. Tools
such as fuzzywuzzy will run in Omega(mn) to find the best-matching strings in
a column of n values compared to the m values of another column, whereas this
model is expected to have a runtime of Omega(m + n) due to the pre-processing
of the right DataFrame columns as a spellchecker corpus that searched using
 the Symmetric Delete spelling correction algorithm. 

This method is best suited for fuzzy searches of large DataFrames due to the
comparatively large amount of pre-processing but faster search performance.

The algorithm operates as follows:
1. A "left" Pandas DataFrame and a "right" Pandas DataFrame are input to
    get_fuzzy_columns with the column names used for comparison.
2. Each right DataFrame is copied into a temporary corpus text file.
3. If text preprocessing is enabled (by default), each entry in the corpus text
    file is preprocessed and copied to another preprocessed text file. An
    in-memory index is created to translate processed strings to preprocessed
    strings.
4. A Symspell object is instantiated and the corpus file is used to create a 
    lookup dictionary.
5. Each record from the left DataFrame is queried from the dictionary using the
    Symspell.lookup function to find the closest string in terms of edit 
    distance, and based on user input the found string (or a substitute string
    if one isn't found) is placed in a new column in the left DataFrame. If
    preprocessing is used, the left DataFrame record is preprocessed, and the
    output found string is back-processed using the in-memory index.
6. When all records of the left DataFrame have been processed, a new column
    containing the results of the fuzzy lookup is added to the left DataFrame,
    usually in a column labeled 'fuzzy_' + queried column name.

Classes:
    Fuzzy: contains methods for creating a Symspell dictionary from the input
        right Pandas DataFrame column and manages queries to the Symspell
        dictionary.

Functions:
    get_fuzzy_columns: primary API to take input Pandas DataFrames and selected
        columns and create new fuzzy columns for later Pandas merging.

loggers:
    '__name__': Module-level logger for debugging, warnings, and errors.

'''

import logging
import os
import fuzzypanda.preprocess as preprocess
from symspellpy.symspellpy import SymSpell, Verbosity


# Setup a default logger
logger = logging.getLogger(__name__)

class Fuzzy:
    ''' 
    This class defines the fuzzy joining tools and parameters for 
    string approximation. The primary toolkit for operations is
    the Symspell module and its associated Python port
    https://github.com/mammothb/symspellpy
    
    The input corpus file must be formatted as a record per row;
    all words on a single line are assumed to be part of a single space-
    separated string.
    
    Args:
        input_corpus: path to a text corpus containing the
            data to which query strings will be searched.
            Default is None, in which case a corpus can be
            loaded later
        preprocesser: an instance of the fuzzypanda.preprocess.PreProcessor
            class containing the 'preprocess' method used to pre-process the
            input strings. If set to None, will instantiate the default
            pre-processor. This option can be used to create a custom 
            pre-processor to pass to the get_fuzzy_columns function.
        max_edit_distance_dictionary: maximum edit distance to consider in
            SymSpell dictionary searches.
        prefix_length: length of the SymSpell dictionary prefix
    
    Attributes:
        corpus: path to the text corpus. If preprocessed, will point
            to the preprocessed file and unprocessed_corpus will
            point to the unprocessed file.
        preprocess_flag: Flag for indicating that preprocessing should
            be completed
        unprocessed_corpus: if pre-processing is requested, will point to
            the file containing the unprocessed input file
        sym_spell: the SymSpell object
        max_edit_distance_dictionary: maximum edit distance to consider in
            SymSpell dictionary searches.
        prefix_length: length of the SymSpell dictionary prefix
        
    '''
    
    
    def __init__(self,
                 input_corpus: str = None,
                 preprocesser=None,
                 max_edit_distance_dictionary: int = 2,
                 prefix_length: int = 7):
        # Set flags and initial variables
        self._preprocess_flag = False
        self.unprocessed_corpus = None
        self.sym_spell = None
        self.index_dictionary = None
        # Set inputs to attributes
        self.corpus = input_corpus
        self.max_edit_distance_dictionary = max_edit_distance_dictionary
        self.prefix_length = prefix_length
        # Setup the pre-processor object
        if preprocesser is None:
            self.preprocesser = preprocess.PreProcessor()
        else:
            self.preprocesser = preprocesser
        # Check the corpus and bootstrap preprocessing and Symspell
        self.check_corpus()
        if preprocess:
            self.preprocess_corpus()
        if self._preprocess_flag:
            self.create_symspell_dict()
            self.create_index()
    
    def is_preprocessed(self):
        '''
        Returns true if the corpus has been processed, false otherwise
        '''
        return(self._preprocess_flag)
    
    def check_corpus(self):
        '''
        Verifies that the corpus file exists
        '''
        logger.debug('Checking corpus file %s', self.corpus)
        if self.corpus is None:
            logger.warning('Corpus file not defined')
            return
        elif not os.path.exists(self.corpus):
            logger.error('Corpus file %s not found', self.corpus)
            raise FileNotFoundError( f'Corpus file {self.corpus} not found')
        else:
            logger.debug('Corpus file found')
            return
        
    def preprocess_corpus(self):
        '''
        Preprocesses the given corpus file in self.corpus. Will copy the
        processed results to 'process_[self.corpus]' file and change the
        self.corpus file to point to it.
        '''
        # Status checking
        logger.debug('Preprocessing corpus file %s', self.corpus)
        if self._preprocess_flag:
            logger.warning('Corpus already preprocessed! Skipping')
            return
        if self.corpus is None:
            logger.error('Attempted to pre-process undefined corpus file')
            raise FileNotFoundError('self.corpus must be specified before'
                                    ' pre-processing')
        self.check_corpus()
        # Creating filenames
        corpus_directory = os.path.dirname(self.corpus)
        corpus_name = os.path.basename(self.corpus)
        processed_corpus = os.path.join(corpus_directory,
                                        'preprocessed_' + corpus_name)
        # Pre-processing the input corpus strings
        with open(self.corpus, 'r') as cf:
            with open(processed_corpus, 'w') as pcf:
                for line in cf:
                    pcf.write(self.preprocesser.preprocess(line) + '\n')
        self.unprocessed_corpus = self.corpus
        self.corpus = processed_corpus
        self._preprocess_flag = True
        logger.debug('Corpus processed to %s', self.corpus)
    
    def create_symspell_dict(self):
        '''
        Creates the SymSpell dictionary object for later lookup. Required
        to lookup strings
        '''
        logger.debug('Creating SymSpell dictionary')
        self.check_corpus()
        # create SymSpell object
        try:
            self.sym_spell = SymSpell(self.max_edit_distance_dictionary,
                                      self.prefix_length)
        except Exception as ex:
            # in case an error occurs in SymSpell
            logger.exception('Failure to create SymSpell object!')
            raise ex
        # Create the dictionary for SymSpell
        self.sym_spell.create_dictionary(self.corpus)

    def create_index(self):
        '''
        The SymSpell dictionary will lookup strings closest to the preprocessed
        version of the query string. To convert back to the original string,
        an index dictionary is created to map back to the original string match.
        This function will create the in-memory dictionary used to lookup the
        original string from the pre-processed string
        The resulting index_dictionary will return strings such that
        index_dictionary[processed string] = unprocessed string
        '''
        logger.debug('Creating corpus index')
        # Status checking
        self.check_corpus()
        if self.index_dictionary is not None:
            logger.warning('index_dictionary already created. Overwritting.')
        if not self._preprocess_flag:
            logger.error('Corpus %s not processed. Cannot create'
                         ' index dictionary', self.corpus)
            raise FileNotFoundError('Corpus not processed. '
                                    'Cannot create index dictionary',
                                     self.corpus)
        if not os.path.exists(self.unprocessed_corpus):
            logger.error('Unprocessed Corpus file %s'
                         'not found', self.unprocessed_corpus)
            raise FileNotFoundError('Unprocessed Corpus file' 
                                    f'{self.unprocessed_corpus} not found')
        # Create pre-process index as dictionary
        self.index_dictionary = {}
        with open(self.unprocessed_corpus, 'r') as ucf:
            for line in ucf:
                # Create the index entries
                original_string = line.strip()
                processed_string = self.preprocesser.preprocess(original_string)
                # Warn if the same string conflicts with an existing entry
                if processed_string in self.index_dictionary:
                    conflict_string = self.index_dictionary[processed_string]
                    # Don't flag if they are the same to begin with
                    if conflict_string != original_string:
                        logger.warning('index_dictionary conflict: '
                                       '%s conflicts with %s for key '
                                       '%s. Keeping index_dictionary[%s] = %s',
                                       original_string,
                                       conflict_string,
                                       processed_string,
                                       processed_string,
                                       conflict_string)
                        continue
                # if no conflict, add to index
                self.index_dictionary.update({processed_string: 
                                              original_string})
        
        logger.debug('Corpus index created')
    
    def query(self, qstring: str):
        '''
        Queries an input string to the corpus, and retrieves 
        the closest value in the corpus by edit distance. 
        
        Args:
            qstring: string to query from the corpus
            
        Returns:
            (term, found_flag): Tuple of the suggested term and a flag
                of True if found in the corpus, or False if not. If not found
                within the corpus, returns the original qstring
        '''
        # Status checks
        # Check qstring
        qstring_type = type(qstring)
        if qstring_type is not type(''):
            msg = f'{qstring} is type {qstring_type} not string'
            logger.error(msg)
            raise ValueError(msg)
        # Check index_dictionary
        if self.index_dictionary is None:
            msg = 'index_dictionary not created'
            logger.error(msg)
            raise ValueError(msg)
        # Check sym_spell
        if self.sym_spell is None:
            msg = 'sym_spell SymSpell object not created'
            logger.error(msg)
            raise ValueError(msg)
        # pre-process the string
        processed_string = self.preprocesser.preprocess(qstring)
        logger.debug('Querying string: \'%s\', preprocessed to \'%s\' ',
                     qstring, processed_string)
        # Look up string using Symspell
        suggest = self.sym_spell.lookup(processed_string,
                                        Verbosity.TOP,
                                        include_unknown=True)
        found_term = suggest[0].term
        found_edit_distance = suggest[0].distance
        # Determine if string is a hit or miss and return result
        if found_edit_distance > self.max_edit_distance_dictionary:
            # indicates a failed lookup
            logger.debug('String \'%s\' not found!', qstring)
            return (qstring, False)
        else:
            # Found a term; backsolve and return found string
            backprocessed_string = self.index_dictionary[found_term]
            logger.debug('String \'%s\' found! Backprocessed \'%s\' to \'%s\'',
                          qstring, found_term, backprocessed_string)
            return (backprocessed_string, True)

    def get_fuzzy_column(self, 
                         dataframe,
                         col_name,
                         null_return=None):
        '''
        Given a Pandas dataframe and the name of a column, returns a new column
        with values taken from a fuzzy search of the underlying dictionary of
        names. 
        
        Args:
            dataframe (pandas.DataFrame): Input dataframe from which column
                values will be taken
            col_name (str): string of the column name used for searching values
            null_return (str): string to return if value is not found in the
                underlying dictionary. If None, will return the input string
                from the old column in the new column. Default is None.

        Returns:
            fuzzy_col (pandas.Series): Output pandas series of query results
            
        Raises:
            LookupError: if col_name is not in dataframe
            ValueError: if null_return is not a string type

        '''
        logger.debug('Creating fuzzy column for %s', col_name)
        # Input checking
        # Check col_name
        if col_name not in dataframe.columns:
            msg = [f'{col_name} not in dataframe columns:']
            for col in dataframe.columns:
                msg.append(col)
            logger.error(' '.join(msg))
            raise LookupError(' '.join(msg))
        # Check null_return
        str_type = type('')
        nr_type = type(null_return)
        if null_return is not None and nr_type is not str_type:
            msg = f'null_return is type {nr_type} not {str_type}'
            logger.error(msg)
            raise ValueError(msg)
        
        # Define a simple lookup function for serial df.apply
        def apply_query(value):
            (out, found) = self.query(value)
            if found:
                return out
            else:
                if null_return is None:
                    return out
                else:
                    return null_return

        fuzzy_col = dataframe[col_name].apply(apply_query)
        return fuzzy_col


def get_fuzzy_columns(left_dataframe,
                      right_dataframe,
                      left_cols,
                      right_cols=None,
                      null_return=None,
                      preprocesser=None,
                      max_edit_distance=2): 
    '''
    Main fuzzy joining API for the fuzzy joining of the given left_dataframe 
    and right_dataframe. Given a string or list of strings to the cols argument,
    this function will add fuzzy columns to the left_dataframe that best match
    the columns of the right_dataframe. This operation can then be followed
    up with a Pandas merge or join to perform the actual joining operation.
    
    Args:
        left_dataframe (pandas.DataFrame): left Pandas dataframe to which
            columns will be added
        right_dataframe (pandas.DataFrame): right Pandas dataframe from which
            fuzzy values in the left dataframe will be compared and suggested
        left_cols (List(str)): A list of strings of column names present in
            left_dataframe that will be compared to the corresponding columns
            in right_dataframe.
        right_cols (List(str)): A list of strings of column names present in
            right_dataframe used for comparison to those in given in 
            left_dataframe. If both dataframes share the column names on which
            fuzzy columns will be created, this parameter can be set to None
            and the values given in left_cols will be used as the names in
            both dataframes. Default is None.
        null_return (string): The string used if a match isn't found. Can be 
            used to set NULL values if a fuzzy match isn't found in the right
            dataframe. Setting to None will return the string used to search for
            the fuzzy value. Default is None.
        preprocesser: an instance of the fuzzypanda.preprocess.PreProcessor
            class containing the 'preprocess' method used to pre-process the
            input strings. If set to None, will instantiate the default
            pre-processor. This option can be used to create a custom 
            pre-processor to pass to the get_fuzzy_columns function.
        max_edit_distance (int): The maximum edit distance that will be 
            considered when comparing columns. The higher the number, the more
            "incorrect" the left columns can be to be searched in the right
            columns. Increasing this number heavily impacts runtime and should
            be set as low as possible. Default is 2.

    Returns:
        Performs an in-place creation of fuzzy columns within left_dataframe.
        Each given left column in left_cols will have a 'fuzzy_' + left_cols
        corresponding to the matched column.
    
    Raises:
        ValueError: if left_cols or right_cols is not a list or None
        LookupError: if left_cols or right_cols are not in their dataframe
        ValueError: if null_return is not None or a string type
        ValueError: if max_edit_distance is < 1
    
    '''
    # Check inputs
    # Check left_cols
    if type(left_cols) is not type(list()):
        msg = f'left_cols must be of type list. Given {type(left_cols)}'
        logger.error(msg)
        raise ValueError(msg)
    for col in left_cols:
        if col not in left_dataframe:
            msg = f'{col} in left_cols not in left_dataframe columns'
            logger.error(msg)
            raise LookupError(msg)
    # Check right_cols
    if right_cols is None:
        logger.debug('right_cols set to None, copying to left_cols')
        right_cols = left_cols
    else:
        if type(right_cols) is not type(list()):
            msg = f'right_cols must be of type list. Given {type(right_cols)}'
            logger.error(msg)
            raise ValueError(msg)
        
        for col in right_cols:
            if col not in right_dataframe:
                msg = f'{col} in right_cols not in right_dataframe columns'
                logger.error(msg)
                raise LookupError(msg)
    # Check null_return
    str_type = type('')
    nr_type = type(null_return)
    if null_return is not None and nr_type is not str_type:
        msg = f'null_return is type {nr_type} not {str_type}'
        logger.error(msg)
        raise ValueError(msg)
    # Check max_edit_distance
    if max_edit_distance < 1:
        msg = f'max_edit_distance must be > 1, given {max_edit_distance}'
        logger.error(msg)
        raise ValueError(msg)
    
    # Create list of fuzzy columns
    fuzzy_cols = []
    for i, left_col in enumerate(left_cols):
        right_col = right_cols[i]
        # create the dictionary text file
        dict_name = right_col + '_dict.txt'
        with open(dict_name, 'w') as dict_file:
            for row in right_dataframe[right_col]:
                dict_file.write(str(row) + '\n')
        fuzz_obj = Fuzzy(input_corpus=dict_name,
                         max_edit_distance_dictionary=max_edit_distance,
                         preprocesser=preprocesser)
        fuzzy_cols.append(fuzz_obj.get_fuzzy_column(dataframe=left_dataframe,
                                                    col_name=left_col,
                                                    null_return=null_return))
        # Remove the corpus files after use
        os.remove(dict_name)  
        os.remove('preprocessed_' + dict_name)
    
    # Add fuzzy columns to the dataframe
    for i, fuzzy_col in enumerate(fuzzy_cols):
        fuzzy_col_name = 'fuzzy_' + left_cols[i]
        left_dataframe[fuzzy_col_name] = fuzzy_col

if __name__ == '__main__':
    pass
