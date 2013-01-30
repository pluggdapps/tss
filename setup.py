# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import re
from   setuptools import setup, find_packages
from   os.path    import abspath, dirname, join

here = abspath( dirname(__file__) )
README = open(join(here, 'README.rst')).read()

v = open(join(dirname(__file__), 'tss', '__init__.py'))
version = re.compile(r".*__version__[ ]*=[ ]*'(.*?)'", re.S).match(v.read()).group(1)
v.close()

description='CSS Extension language'

classifiers = [
'Development Status :: 4 - Beta',
'Environment :: Web Environment',
'Intended Audience :: Developers',
'Programming Language :: Python :: 2.6',
'Programming Language :: Python :: 2.7',
'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
]

setup(
    name='tss',
    version=version,
    py_modules=[],
    package_dir={},
    packages=find_packages(),
    ext_modules=[],
    scripts=[],
    data_files=[],
    package_data={},                        # setuptools / distutils
    include_package_data=True,              # setuptools
    exclude_package_data={},                # setuptools
    zip_safe=False,                         # setuptools
    entry_points={                          # setuptools
    },
    install_requires=[                      # setuptools
        'ply>=3.4',
    ],
    extras_require={},                      # setuptools
    setup_requires={},                      # setuptools
    dependency_links=[],                    # setuptools
    namespace_packages=[],                  # setuptools
    test_suite='tss.test',                  # setuptools

    provides=[ 'tss', ],
    requires='',
    obsoletes='',

    author='Pratap R Chakravarthy',
    author_email='prataprc@gmail.com',
    maintainer='Pratap R Chakravarthy',
    maintainer_email='prataprc@gmail.com',
    url='http://tss.pluggdapps.com',
    download_url='',
    license='Simplified BSD license',
    description=description,
    long_description=README,
    platforms='',
    classifiers=classifiers,
    keywords=[ 'template, web, html, css' ],
)
