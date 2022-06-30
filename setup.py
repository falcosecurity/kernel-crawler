#!/usr/bin/env python

from setuptools import setup, find_packages


setup(name='kernel_crawler',
      version='1.0.0',
      description='Falcosecurity kernel crawler',
      author='Grzegorz Nosek',
      author_email='grzegorz.nosek@sysdig.com',
      url='https://falco.org/',
      packages=find_packages(),
      install_requires=[
          'click',
          'requests',
          'lxml',
          'docker',
      ],
)
