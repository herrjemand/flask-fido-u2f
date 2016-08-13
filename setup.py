"""
Flask-FIDO-U2F
-------------

Flask plugin to simplify usage and management of U2F devices.
"""
from setuptools import setup

setup(
    name                 = 'Flask-FIDO-U2F',
    version              = '0.4.0',
    url                  = 'https://github.com/herrjemand/flask-fido-u2f',
    license              = 'MIT',
    author               = 'Ackermann Yuriy',
    author_email         = 'ackermann.yuriy@gmail.com',
    description          = 'A Flask plugin that adds FIDO U2F support.',
    long_description     =  read('README.md'),
    keywords             = 'flask fido u2f 2fa',

    py_modules           = ['flask_fido_u2f'],
    zip_safe             = True,
    test_suite           = 'test',
    tests_require        = [],
    include_package_data = True,
    platforms            = 'any',
    install_requires     = [
        'Flask',
        'python-u2flib-server'
    ],
    classifiers          = [
        'Environment :: Web Environment',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        # Needs python 2.x testing
        # 'Programming Language :: Python :: 2',
        # 'Programming Language :: Python :: 2.6',
        # 'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Internet',
        'Topic :: Security :: Cryptography',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)