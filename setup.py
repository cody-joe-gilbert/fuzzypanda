from setuptools import setup

def readme():
    with open('README.md') as f:
        return f.read()

setup(name='fuzzypanda',
      version='0.1.1',
      description='Toolkit for performing fuzzy joins with Symspell framework',
      long_description=readme(),
      long_description_content_type='text/markdown',
      url='https://github.com/cody-joe-gilbert/fuzzypanda',
      author='Cody Joe Gilbert',
      author_email='cody@codyjoe.com',
      license='MIT',
      keywords='fuzzy join pandas Symspell',
      classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Operating System :: OS Independent',
        'Topic :: Scientific/Engineering :: Information Analysis',
      ],
      packages=['fuzzypanda'],
      install_requires=[
          'symspellpy',
      ],
      python_requires='>=3',
      zip_safe=False)