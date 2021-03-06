#!/usr/bin/env python

from setuptools import setup
import versioneer


setup(
    name='zish',
    version=versioneer.get_version(),
    description='A Python 3 library for the Zish format.',
    author='Tony Locke',
    author_email='tlocke@tlocke.org.uk',
    url='https://github.com/tlocke/zish_python',
    cmdclass=versioneer.get_cmdclass(),
    packages=[
        'zish'
    ],
    install_requires=[
        'arrow==0.15.5'
    ]
)
