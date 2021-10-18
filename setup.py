#!/usr/bin/env python

from distutils.core import setup

setup(name='probe_builder',
      version='1.0',
      description='Sysdig probe builder',
      author='Grzegorz Nosek',
      author_email='grzegorz.nosek@sysdig.com',
      url='https://www.sysdig.com/',
      packages=['probe_builder'],
      install_requires=[
          'click',
          'requests',
          'lxml',
      ],
      entry_points={
          'console_scripts': [
              'probe_builder = probe_builder:cli',
              'artifactory_download = probe_builder.artifactory_download:cli',
          ],
      },
      )
