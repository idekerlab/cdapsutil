#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
from setuptools import setup

with open(os.path.join('cdapsutil', '__init__.py')) as ver_file:
    for line in ver_file:
        if line.startswith('__version__'):
            version = re.sub("'", "", line[line.index("'"):])

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'ndex2',
    'requests',
    'tqdm'
]

test_requirements = [
    'requests-mock'
]

setup(
    name='cdapsutil',
    version=version,
    description="Python utilities for CDAPS",
    long_description=readme + '\n\n' + history,
    author="Christopher Churas",
    author_email='churas.camera@gmail.com',
    url='https://github.com/idekerlab/cdapsutil',
    packages=[
        'cdapsutil',
    ],
    package_dir={'cdapsutil':
                 'cdapsutil'},
    data_files=[('style', ['cdapsutil/default_style.cx']),
                ],
    include_package_data=True,
    install_requires=requirements,
    license="BSD license",
    zip_safe=False,
    keywords='cdapsutil',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
