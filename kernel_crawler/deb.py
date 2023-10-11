# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2023 The Falco Authors.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
    # http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#!/usr/bin/env python

from __future__ import print_function

import re
import sys

import click
import logging
import requests

from lxml import html

from . import repo
from kernel_crawler.utils.download import get_first_of, get_url
from kernel_crawler.utils.py23 import make_bytes, make_string
import pprint

logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(depth=4)


class IncompletePackageListException(Exception):
    pass


class DebRepository(repo.Repository):

    def __init__(self, repo_base, repo_name):
        self.repo_base = repo_base
        self.repo_name = repo_name

    def __str__(self):
        return self.repo_base + self.repo_name

    @classmethod
    def scan_packages(cls, stream):
        """
        Parse a Packages file into individual packages metadata.
        """
        current_package = {}
        packages = {}
        for line in stream:
            line = make_string(line)
            line = line.rstrip()
            if line == '':
                name = current_package['Package']
                depends = current_package.get('Depends', [])
                packages[name] = {
                    'Depends': set(depends),
                    'Version': current_package['Version'],
                    'Filename': current_package['Filename'],
                }
                current_package = {}
                continue
            # ignore multiline values
            if line.startswith(' '):
                continue
            try:
                key, value = line.split(': ', 1)
                if key in ('Provides', 'Depends'):
                    value = value.split(', ')
            except ValueError:
                print(line)
                raise
            current_package[key] = value

        if current_package:
            name = current_package['Package']
            depends = current_package.get('Depends', [])
            packages[name] = {
                'Depends': set(depends),
                'Version': current_package['Version'],
                'Filename': current_package['Filename'],
            }

        return packages

    KERNEL_PACKAGE_PATTERN = re.compile(r'^linux-.*?-[0-9]\.[0-9]+\.[0-9]+')
    KERNEL_RELEASE_UPDATE = re.compile(r'^([0-9]+\.[0-9]+\.[0-9]+-[0-9]+)\.(.+)')

    @classmethod
    def is_kernel_package(cls, dep):
        return (cls.KERNEL_PACKAGE_PATTERN.search(dep) and
                not dep.endswith('-dbg') and
                'modules-extra' not in dep and
                'linux-source' not in dep and
                'tools' not in dep) or 'linux-kbuild' in dep

    @classmethod
    def filter_kernel_packages(cls, deps):
        return [dep for dep in deps if (cls.is_kernel_package(dep))]

    @classmethod
    def transitive_dependencies(cls, packages, pkg_name, dependencies=None, level=0, cache=None):
        if cache is None:
            cache = {}
        if dependencies is None:
            dependencies = {pkg_name}
        pkg_deps = cls.filter_kernel_packages(packages[pkg_name]['Depends'])
        for dep in pkg_deps:
            dep = dep.split(None, 1)[0]
            # Note: this always takes the first branch of alternative
            # dependencies like 'foo|bar'. In the kernel crawler, we don't care
            #
            # also, apparently libc6 and libgcc1 depend on each other
            # so we only filter for kernel packages
            if dep in packages:
                if dep not in dependencies:
                    if dep not in cache:
                        dependencies |= {dep}
                        deps = {dep}
                        deps |= cls.transitive_dependencies(packages, dep, dependencies, level + 1, cache)
                        cache[dep] = deps
                    dependencies |= cache[dep]
            else:
                raise (IncompletePackageListException("{} not in package list".format(dep)))
        return dependencies

    @classmethod
    def get_package_deps(cls, packages, pkg):
        all_deps = set()
        if not cls.is_kernel_package(pkg):
            return set()
        for dep in cls.filter_kernel_packages(cls.transitive_dependencies(packages, pkg)):
            all_deps.add(packages[dep]['URL'])
        return all_deps


    # this method returns a list of available kernel-looking package _names_
    # (i.e., without version) available from within an individual .deb repository
    def get_package_list(self, packages, package_filter):
        kernel_packages = []
        for p in packages.keys():
            if not p.startswith('linux-headers-'):
                continue
            release = p.replace('linux-headers-', '')
            if 'linux-modules-{}'.format(release) in packages:
                kernel_packages.append(p)
                kernel_packages.append('linux-modules-{}'.format(release))
            elif 'linux-image-{}'.format(release) in packages:
                kernel_packages.append(p)
                kernel_packages.append('linux-image-{}'.format(release))

        if not package_filter:
            logger.debug("kernel_packages[{}]=\n{}".format(str(self), pp.pformat(kernel_packages)))
            return kernel_packages
            # return [dep for dep in kernel_packages if self.is_kernel_package(dep) and not dep.endswith('-dbg')]

        kernel_packages = set(kernel_packages)
        linux_modules = 'linux-modules-{}'.format(package_filter)
        linux_headers = 'linux-headers-{}'.format(package_filter)
        linux_image = 'linux-image-{}'.format(package_filter)
        # if the filter is an exact match on package name, just pick that
        if package_filter in packages:
            return [package_filter]
        # if the filter is an exact match on the suffix for headers and modules, use both
        elif linux_modules in kernel_packages and linux_headers in kernel_packages:
            return [linux_modules, linux_headers]
        # same for image
        elif linux_image in kernel_packages and linux_headers in kernel_packages:
            return [linux_image, linux_headers]
        # otherwise just pick up anything matching it
        else:
            return [k for k in kernel_packages if package_filter in k]

    def get_raw_package_db(self):
        try:
            repo_packages = get_first_of([
                self.repo_base + self.repo_name + '/Packages.xz',
                self.repo_base + self.repo_name + '/Packages.gz',
            ])
        except requests.HTTPError:
            return {}

        if repo_packages:
            repo_packages = repo_packages.splitlines(True)
            packages = self.scan_packages(repo_packages)
            for name, details in packages.items():
                details['URL'] = self.repo_base + details['Filename']
            return packages
        else:
            return {}

    @classmethod
    def build_package_tree(cls, packages, package_list):
        # this classmethod takes as input:
        #  - packages, a dictionary of .deb packages with their metadata
        #  - packages_list, a list of strings (package names)
        # it traverses the dependency chain within the package_list
        # and returns a dictionary of urls:
        # {'5.15.0-1001/2': {'http://security.ubuntu.com/ubuntu/pool/main/l/linux-azure/linux-azure-headers-5.15.0-1001_5.15.0-1001.2_all.deb',
        #           'http://security.ubuntu.com/ubuntu/pool/main/l/linux-azure/linux-headers-5.15.0-1001-azure_5.15.0-1001.2_amd64.deb',
        #           'http://security.ubuntu.com/ubuntu/pool/main/l/linux-azure/linux-modules-5.15.0-1001-azure_5.15.0-1001.2_amd64.deb',
        #           'http://security.ubuntu.com/ubuntu/pool/main/l/linux-signed-azure/linux-image-5.15.0-1001-azure_5.15.0-1001.2_amd64.deb'},

        deps = {}
        logger.debug("packages=\n{}".format(pp.pformat(packages)))
        logger.debug("package_list=\n{}".format(pp.pformat(package_list)))
        with click.progressbar(package_list, label='Building dependency tree', file=sys.stderr,
                               item_show_func=repo.to_s) as pkgs:
            for pkg in pkgs:
                pv = packages[pkg]['Version']
                m = cls.KERNEL_RELEASE_UPDATE.match(pv)
                if m:
                    pv = '{}/{}'.format(m.group(1), m.group(2))
                try:
                    logger.debug("Building dependency tree for {}, pv={}".format(str(pkg), pv))
                    deps.setdefault(pv, set()).update(cls.get_package_deps(packages, pkg))
                except IncompletePackageListException:
                    logger.debug("No dependencies found for {}, pv={}".format(str(pkg), pv))
                    pass

        logger.debug("before pruning, deps=\n{}".format(pp.pformat(deps)))
        for pkg, dep_list in list(deps.items()):
            have_headers = False
            for dep in dep_list:
                if 'linux-headers' in dep:
                    have_headers = True
            if not have_headers:
                del deps[pkg]
        logger.debug("after pruning, deps=\n{}".format(pp.pformat(deps)))
        return deps

    def get_package_tree(self, filter=''):
        packages = self.get_raw_package_db()
        package_list = self.get_package_list(packages, filter)
        return self.build_package_tree(packages, package_list)


class DebMirror(repo.Mirror):

    def __init__(self, base_url, arch, repo_filter=None):
        self.base_url = base_url
        if repo_filter is None:
            repo_filter = lambda _: True
        self.repo_filter = repo_filter
        super().__init__(arch)

    def __str__(self):
        return self.base_url

    def scan_repo(self, dist):
        repos = {}
        all_comps = set()
        release = get_url(self.base_url + dist + 'Release')
        if release:  # if release exists
            for line in release.splitlines(False):
                if line.startswith(make_bytes('Components: ')):
                    for comp in line.split(None)[1:]:
                        comp = make_string(comp)
                        if comp in ('main', 'updates', 'updates/main'):
                            if dist.endswith('updates/') and comp.startswith('updates/'):
                                comp = comp.replace('updates/', '')
                            all_comps.add(comp)
                    break
            for comp in all_comps:
                url = dist + comp + '/binary-' + self.arch + '/'
                repos[url] = DebRepository(self.base_url, url)
        return repos

    def list_repos(self):
        dists_url = self.base_url + 'dists/'
        dists = requests.get(dists_url)
        dists.raise_for_status()
        dists = dists.content
        doc = html.fromstring(dists, dists_url)
        dists = [dist for dist in doc.xpath('/html/body//a[not(@href="../")]/@href')
                 if dist.endswith('/')
                 and not dist.startswith('/')
                 and not dist.startswith('?')
                 and not dist.startswith('http')
                 and self.repo_filter(dist)
                 ]

        repos = {}
        with click.progressbar(
                dists, label='Scanning {}'.format(self.base_url), file=sys.stderr, item_show_func=repo.to_s) as dists:
            for dist in dists:
                try:
                    repos.update(self.scan_repo('dists/{}'.format(dist)))
                except requests.HTTPError:
                    pass
                try:
                    repos.update(self.scan_repo('dists/{}updates/'.format(dist)))
                except requests.HTTPError:
                    pass

        return sorted(repos.values(), key=str)
