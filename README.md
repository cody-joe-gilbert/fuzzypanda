
# FuzzyPanda

FuzzyPanda was created to support fuzzy join operations with [Pandas]( https://pandas.pydata.org/ ) [DataFrames]( https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html ) using Python Ver. 3. These fuzzy joins are a form of [approximate string matching]( https://en.wikipedia.org/wiki/Approximate_string_matching ) to join relational data that contain "errors" or minor modifications that preclude direct string comparison. 

FuzzyPanda will match strings that

1. Are within a user-specified [edit distance]( https://en.wikipedia.org/wiki/Edit_distance ) (e.g. "test" == "taste" with edit distance 2)
2. Are independent of case (e.g. "Test" == "test")
3. Are Whitespace-delimited strings are matched regardless of token order (e.g. "dark and stormy night" == "stormy and dark night")
4. Are independent of special symbols (e.g. "this-string" == "this string")

The criteria in steps 2-4 can be modified via modification of the `fuzzypanda.preprocess.PreProcessor` class. 

The primary API is the `fuzzypanda.get_fuzzy_columns` function that takes two Pandas DataFrames and a set of column names, and creates a new column in the "left" DataFrame that contains the closest entries by string edit distance to the associated values in the "right" DataFrame columns. The Pandas `merge` or `join` functions can later be used to perform full joins on the DataFrames.

### Installation

FuzzyPanda can be installed using `pip`:

```shell
pip install fuzzypanda
```

### Usage

This version of FuzzyPanda currently supports the `fuzzypanda.get_fuzzy_columns` function. More functions are expected in future releases.

#### Create Fuzzy Matched Columns

Main fuzzy joining API for the fuzzy joining of the given `left_dataframe` and `right_dataframe`. Given a string or list of strings to the cols argument, this function will add fuzzy columns to the `left_dataframe` that best match the columns of the `right_dataframe`. This operation can then be followed up with a Pandas `merge` or `join` to perform the actual joining operation.

```python
fuzzypanda.get_fuzzy_columns(left_dataframe,
									right_dataframe,
									left_cols,
									right_cols=None,
									null_return=None,
									preprocesser=None,
									max_edit_distance=2): 
```

* Arguments:
	* `left_dataframe` (pandas.DataFrame): left Pandas dataframe to which columns will be added
	* `right_dataframe` (pandas.DataFrame): right Pandas dataframe from which fuzzy values in the `left_dataframe` will be compared and suggested
	* `left_cols` (List(str)): A list of strings of column names present in `left_dataframe` that will be compared to the corresponding columns in `right_dataframe`.
	* `right_cols` (List(str)): A list of strings of column names present in `right_dataframe` used for comparison to those in given in `left_dataframe`. If both dataframes share the column names on which fuzzy columns will be created, this parameter can be set to `None` and the values given in `left_cols` will be used as the names in both dataframes. Default is `None`.
	* `null_return` (string): The string used if a match isn't found. Can be used to set NULL values if a fuzzy match isn't found in the `right_dataframe`. Setting to `None` will return the string used to search for the fuzzy value. Default is `None`.
	* `preprocesser`: an instance of the `fuzzypanda.preprocess.PreProcessor` class containing the `preprocess` method used to pre-process the input strings. If set to `None`, will instantiate the default pre-processor. This option can be used to create a custom pre-processor to pass to the `get_fuzzy_columns` function. Default is `None`
	* `max_edit_distance` (int): The maximum edit distance that will be considered when comparing columns. The higher the number, the more "incorrect" the `left_dataframe` columns can be to be searched in the `right_dataframe` columns. Increasing this number heavily impacts runtime and should be set as low as possible. Default is 2.
* Returns: Performs an in-place creation of fuzzy columns within `left_dataframe`. Each given left column in `left_cols` will have a `'fuzzy_' + left_col_name` corresponding to the matched column.

####  get\_fuzzy\_columns Example 
Suppose you wish to join the following two dataframes on columns `col_1` and `col_2`, where the columns in `left_df` contain entries that are misspelled and/or jumbled tokens of those in `right_df`:

```python
print(left_df)
>        ID              col_1            col_2
> 0  123314             kitten             oboe
> 1  123213             siting          trvmpet
> 2   43543  the times of best  over te rainbow 
> 3   35435    the worst times    in Symphony C 
> 4     987       not in there     not in there

print(right_df)
>          ID               col_1             col_2
> 0  12783314              kitten              oboe
> 1  12352213             sitting           trumpet
> 2  43233543   the best of times  over the rainbow
> 3  23432420  the worst of times    Symphony in C#
```

We can now call `fuzzypanda.get_fuzzy_columns`. Notice that the results are columns added to `left_df` in-place, rather than returning a new DataFrame.

```python
fuzzypanda.get_fuzzy_columns(left_dataframe=left_df,
                      		   right_dataframe=right_df,
                      		   left_cols=['col_1', 'col_2'])

print(left_df)
>        ID              col_1            col_2         fuzzy_col_1 \
> 0  123314             kitten             oboe              kitten   
> 1  123213             siting          trvmpet             sitting   
> 2   43543  the times of best  over te rainbow   the best of times   
> 3   35435    the worst times    in Symphony C  the worst of times   
> 4     987       not in there     not in there        not in there
> 
>         fuzzy_col_2  
> 0              oboe  
> 1           trumpet  
> 2  over the rainbow  
> 3    Symphony in C#  
> 4      not in there 
```

### Methodology

This package uses the Symspell Python port [symspellpy by mammothb]( https://github.com/mammothb/symspellpy ) of the original C# implementation of [Symspell by Wolf Garbe]( https://github.com/wolfgarbe/SymSpell ). This fuzzy column creation approach applies a Pandas-friendly wrapper around the Symspell Symmetric Delete spelling correction algorithm to allow substantially faster fuzzy joining. Tools such as fuzzywuzzy will run in Omega(mn) to find the best-matching strings in a column of n values compared to the m values of another column, whereas this model is expected to have a runtime of Omega(m + n) due to the pre-processing of the right DataFrame columns as a spellchecker corpus that searched using  the Symmetric Delete spelling correction algorithm. 

This method is best suited for fuzzy searches of large DataFrames due to the comparatively large amount of pre-processing but faster search performance.

The algorithm operates as follows:

1. A "left" Pandas DataFrame and a "right" Pandas DataFrame are input to `get_fuzzy_columns` with the column names used for comparison.
2. Each right DataFrame is copied into a temporary corpus text file.
3. Each entry in the corpus text file is preprocessed using either the default `fuzzypanda.preprocess.PreProcessor` or a user-supplied object containing a `preprocessor` method and copied to another preprocessed text file. An in-memory index is created to translate processed strings to preprocessed strings.
4. A symspellpy object is instantiated and the corpus file is used to create a lookup dictionary.
5. Each record from the left DataFrame is preprocessed and queried from the dictionary using the `symspellpy.lookup` function to find the closest string in terms of edit distance, and the suggested string (or a substitute string if one isn't found) is placed in an intemediate list.
6. When all records of the left DataFrame have been processed, a new column containing the results of the fuzzy lookup is added to the left DataFrame in a column labeled 'fuzzy_' + queried column name.

### Future Work

* Directly implement pandas `merge` and `join`
* Replace `symspellpy` with a C++ implementation of Symspell to speed lookup calculations
* Create option for multiprocessing and multithreading column record queries.
* Add API to directly process CSV files
* Add API to use Pandas DataFrame chunks
* Expand functionality to use SparkSQL DataFrames



