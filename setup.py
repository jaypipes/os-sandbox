#!/usr/bin/env python

PROJECT = 'os-sandbox'
PROJECT_URL = 'https://github.com/jaypipes/os-sandbox'
VERSION = '0.1'
AUTHOR = 'Jay Pipes'
AUTHOR_EMAIL = '<jaypipes@gmail.com'
DESCRIPTION = 'Easily create virtualized, isolated OpenStack environments.'

from setuptools import setup, find_packages

try:
    LONG_DESCRIPTION = open('README.md', 'rt').read()
except:
    LONG_DESCRIPTION = ''

setup(
    name=PROJECT,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    url=PROJECT_URL,
    download_URL=PROJECT_URL + '/tarball/master',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Intended Audience :: Developer',
        'Environment :: Console',
    ],
    platforms=[
        'Linux',
    ],
    scripts=[],
    provides=[],
    install_requires=[
        'cliff',
        'six',
        'slugify',
    ],
    namespace_packages=[],
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'os-sandbox = os_sandbox.main:main',
        ],
        'os_sandbox': [
            'setup = os_sandbox.cmd.setup:Setup',
            'image list = os_sandbox.cmd.image:ImageList',
            'template list = os_sandbox.cmd.template:TemplateList',
            'template show = os_sandbox.cmd.template:TemplateShow',
            'sandbox list = os_sandbox.cmd.sandbox:SandboxList',
            'sandbox show = os_sandbox.cmd.sandbox:SandboxShow',
            'sandbox start = os_sandbox.cmd.sandbox:SandboxStart',
            'sandbox stop = os_sandbox.cmd.sandbox:SandboxStop',
            'sandbox create = os_sandbox.cmd.sandbox:SandboxCreate',
            'sandbox delete = os_sandbox.cmd.sandbox:SandboxDelete',
        ],
    },
    zip_safe=False,
)
