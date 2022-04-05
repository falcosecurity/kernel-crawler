#!/usr/bin/env python

from distutils.core import setup

setup(name='kernel_crawler',
      version='1.0.0',
      description='Falcosecurity kernel crawler',
      author='Grzegorz Nosek',
      author_email='grzegorz.nosek@sysdig.com',
      url='https://falco.org/',
      packages=['kernel_crawler'],
      install_requires=[
          'click',
          'requests',
          'lxml',
      ],
)
