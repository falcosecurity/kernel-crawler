#!/usr/bin/env python

from setuptools import setup, find_packages


setup(name='kernel-crawler',
      version='1.0.0',
      description='Falcosecurity kernel crawler',
      author='Grzegorz Nosek',
      author_email='grzegorz.nosek@sysdig.com',
      url='https://falco.org/',
      entry_points = {
              'console_scripts': [
                  'kernel-crawler = kernel_crawler.main:cli',                  
              ],              
      },
      packages=find_packages(),
      install_requires=[
          'click',
          'requests',
          'lxml',
          'docker',
          'semantic-version',
          'pygit2',
          'beautifulsoup4'
      ],
)
