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
import traceback

import requests
from lxml import etree, html
import sqlite3
import tempfile
import re
import io

from . import repo
from kernel_crawler.utils.download import get_url

class RpmRepository(repo.Repository):
    def __init__(self, base_url):
        self.base_url = base_url

    def __str__(self):
        return self.base_url

    @classmethod
    def get_loc_by_xpath(cls, text, expr):
        e = etree.fromstring(text)
        loc = e.xpath(expr, namespaces={
            'common': 'http://linux.duke.edu/metadata/common',
            'repo': 'http://linux.duke.edu/metadata/repo',
            'rpm': 'http://linux.duke.edu/metadata/rpm'
        })

        # if unable to find the expression in the XML, return None
        if not loc:
            return None

        # else return the first item out of the tuple
        return loc[0]

    @classmethod
    def kernel_package_query(cls):
        return '''name IN ('kernel', 'kernel-devel', 'kernel-ml', 'kernel-ml-devel')'''

    @classmethod
    def kernel_package_match(cls, name):
        '''
        Python equivalent of kernel_package_query(), used to select the kernel packages
        when a repository ships only the primary XML metadata (see parse_primary_xml()).
        Subclasses overriding kernel_package_query() must override this method too.
        '''
        return name in ('kernel', 'kernel-devel', 'kernel-ml', 'kernel-ml-devel')

    @classmethod
    def build_base_query(cls, filter=''):
        base_query = '''SELECT version || '-' || release || '.' || arch, pkgkey FROM packages WHERE {}'''.format(
            cls.kernel_package_query())
        if not filter:
            return base_query, ()
        else:
            # if filtering, match anythint like 5.6.6 (version) or 5.6.6-300.fc32 (version || '-' || release)
            return base_query + ''' AND (version = ? OR version || '-' || "release" = ?)''', (filter, filter)

    @classmethod
    def parse_repo_db(cls, repo_db, filter=''):
        db = sqlite3.connect(repo_db)
        cursor = db.cursor()

        base_query, args = cls.build_base_query(filter)
        query = '''WITH RECURSIVE transitive_deps(version, pkgkey) AS (
                {}
                UNION
                SELECT transitive_deps.version, provides.pkgkey
                    FROM provides
                    INNER JOIN requires USING (name, flags, epoch, version, "release")
                    INNER JOIN transitive_deps ON requires.pkgkey = transitive_deps.pkgkey
            ) SELECT transitive_deps.version, location_href FROM packages INNER JOIN transitive_deps using(pkgkey);
        '''.format(base_query)

        cursor.execute(query, args)
        return cursor.fetchall()

    @classmethod
    def parse_primary_xml(cls, primary_xml, filter=''):
        '''
        Parse the primary XML metadata and return (version-release.arch, location_href) tuples
        for the kernel packages, like parse_repo_db() does with the sqlite database.

        Unlike parse_repo_db(), this does not resolve the transitive dependencies of the kernel
        packages (the XML metadata would require a manual requires/provides resolution): only
        the kernel packages themselves are returned. This is enough for the distros whose
        to_driverkit_config() just picks the *-devel package (e.g. Photon OS).
        '''
        ns = '{http://linux.duke.edu/metadata/common}'
        packages = []
        for _, pkg in etree.iterparse(io.BytesIO(primary_xml), tag=ns + 'package'):
            if cls.kernel_package_match(pkg.findtext(ns + 'name', default='')):
                ver = pkg.find(ns + 'version')
                version, release = ver.get('ver'), ver.get('rel')
                # same filter semantics as build_base_query(): match either the version
                # (e.g. 5.10.103) or the version-release (e.g. 5.10.103-1.ph4)
                if not filter or filter in (version, version + '-' + release):
                    packages.append((
                        version + '-' + release + '.' + pkg.findtext(ns + 'arch'),
                        pkg.find(ns + 'location').get('href')))
            # the XML of a large repository lists tens of thousands of packages:
            # free each element once processed to keep the memory usage low
            pkg.clear()
            while pkg.getprevious() is not None:
                del pkg.getparent()[0]
        return packages

    def get_repodata_url(self, repomd, data_type):
        '''
        Given the content of repomd.xml, return the URL of the metadata of the given type
        (e.g. 'primary_db' for the sqlite database, 'primary' for the XML), or None if the
        repository does not ship it.
        '''
        href = self.get_loc_by_xpath(
            repomd, f'//repo:repomd/repo:data[@type="{data_type}"]/repo:location/@href')
        if not href:
            return None
        return self.base_url + href

    def get_repodb_url(self):
        repomd = get_url(self.base_url + 'repodata/repomd.xml')
        if not repomd:
            return None
        return self.get_repodata_url(repomd, 'primary_db')

    def get_package_tree(self, filter=''):
        packages = {}
        try:
            repomd = get_url(self.base_url + 'repodata/repomd.xml')
            if not repomd:
                return {}
            # prefer the sqlite database, which also resolves the transitive dependencies of
            # the kernel packages; fall back to the primary XML metadata when a repository
            # does not ship the sqlite database at all (e.g. some Photon OS repositories)
            repodb_url = self.get_repodata_url(repomd, 'primary_db')
            if repodb_url:
                repodb = get_url(repodb_url)
                if not repodb:
                    return {}
                with tempfile.NamedTemporaryFile() as tf:
                    tf.write(repodb)
                    tf.flush()
                    pkgs = self.parse_repo_db(tf.name, filter)
            else:
                primary_url = self.get_repodata_url(repomd, 'primary')
                if not primary_url:
                    print(f"[ERROR] No primary_db nor primary metadata in "
                          f"{self.base_url}repodata/repomd.xml")
                    return {}
                primary = get_url(primary_url)
                if not primary:
                    return {}
                pkgs = self.parse_primary_xml(primary, filter)
        except requests.exceptions.RequestException:
            traceback.print_exc()
            return {}
        for version, url in pkgs:
            packages.setdefault(version, set()).add(self.base_url + url)
        return packages


class RpmMirror(repo.Mirror):

    def __init__(self, base_url, variant, repo_filter=None):
        self.base_url = base_url
        self.variant = variant
        if repo_filter is None:
            repo_filter = lambda _: True
        self.repo_filter = repo_filter
        self.url = base_url

    def __str__(self):
        return self.base_url

    def dist_url(self, dist):
        return '{}{}{}'.format(self.base_url, dist, self.variant)

    def dist_exists(self, dist):
        try:
            r = requests.get(
                self.dist_url(dist),
                headers={  # some URLs require a user-agent, otherwise they return HTTP 406 - this one is fabricated
                    'user-agent': 'dummy'
                },
                timeout = 15
            )
            r.raise_for_status()
        except requests.exceptions.RequestException:
            return False
        return True

    def list_repos(self):
        dists = requests.get(
            self.base_url, 
            headers={  # some URLs require a user-agent, otherwise they return HTTP 406 - this one is fabricated
                'user-agent': 'dummy'
            },
            timeout = 15
        )
        dists.raise_for_status()
        dists = dists.content
        doc = html.fromstring(dists, self.base_url)
        dists = doc.xpath('/html/body//a[not(@href="../")]/@href')
        return [RpmRepository(self.dist_url(dist)) for dist in dists
                if dist.endswith('/')
                and not dist.startswith('/')
                and not dist.startswith('?')
                and not dist.startswith('http')
                and self.repo_filter(dist)
                and self.dist_exists(dist)
                ]


class SUSERpmMirror(RpmMirror):

    def __init__(self, base_url, variant, arch, repo_filter=None):
        '''
        SUSERpmMirror looks like a regular RpmMirror, except that it requires
        the arch in the constructor. The arch is used for passing through to SUSERpmRepository,
        which uses the arch to query for the correct kernel-default-devel out of the package listing.
        '''
        self.base_url = base_url
        self.variant = variant
        self.arch = arch
        if repo_filter is None:
            repo_filter = lambda _: True
        self.repo_filter = repo_filter
        self.url = base_url

    def list_repos(self):
        '''
        Overridden from RpmMirror exchanging RpmRepository for SUSERpmRepository.
        '''
        dists = requests.get(
            self.base_url,
            headers={  # some URLs require a user-agent, otherwise they return HTTP 406 - this one is fabricated
                'user-agent': 'dummy'
            },
            timeout = 15
        )
        dists.raise_for_status()
        dists = dists.content
        doc = html.fromstring(dists, self.base_url)
        dists = doc.xpath('/html/body//a[not(@href="../")]/@href')
        ret = [SUSERpmRepository(self.dist_url(dist), self.arch) for dist in dists
                if dist.endswith('/')
                and not dist.startswith('/')
                and not dist.startswith('?')
                and not dist.startswith('http')
                and self.repo_filter(dist)
                and self.dist_exists(dist)
                ]

        return ret

class SUSERpmRepository(RpmRepository):

    # the kernel headers package name pattern to search for in the package listing XML
    _kernel_devel_pattern = 'kernel-default-devel-'

    def __init__(self, base_url, arch):
        '''
        Constructor, which sets the base URL and the arch.
        The arch is used for finding the correct package in the repomd.
        '''
        self.base_url = base_url
        self.arch = arch

    def get_repodb_url(self):
        '''
        SUSE stores their primary package listing under a different path in the XML from a normal RPM repomd.
        '''
        repomd = get_url(self.base_url + 'repodata/repomd.xml')
        if not repomd:
            return None
        pkglist_url = self.get_loc_by_xpath(repomd, '//repo:repomd/repo:data[@type="primary"]/repo:location/@href')

        # if no pkglist was found, return None
        if not pkglist_url:
            return None

        # else add the pkglist_url to the base_url
        return self.base_url + pkglist_url

    def parse_kernel_release(self, kernel_devel_pkg):
        '''
        Given the kernel devel package string, parse it for the kernel release
        by trimming off the front bits of the string and the extension.

        Example:
            x86_64/kernel-default-devel-5.14.21-150400.22.1.x86_64.rpm -> 5.14.21-150400.22.1.x86_64
        '''
        trimmed = kernel_devel_pkg.replace(f'{self.arch}/{self._kernel_devel_pattern}', '')
        version = trimmed.replace('.rpm', '')

        return version

    def build_kernel_devel_noarch_url(self, kernel_release):
        '''
        A simple method for building the noarch kernel-devel package using the kernel release.
        The kernel release will contain the package arch, but kernel-devel will be a noarch package.
        '''
        return f'{self.base_url}noarch/kernel-devel-{kernel_release}.rpm'.replace(self.arch, 'noarch')

    def open_repo(self, repo_path):
        package_match = f'{self.arch}/{self._kernel_devel_pattern}'
        # regex searching through a file is more memory efficient
        # than parsing the xml into an object structure with lxml etree
        with open(repo_path, mode='r') as f:
            text = str(f.read())
            search = re.search(f'.*href="({package_match}.*rpm)', text)
            if search:
                return search.group(1)
            return None
        return None

    def get_package_tree(self, filter=''):
        '''
        Build the package tree for SUSE, which finds the repomd, parses it for the primary package listing,
        and queries for the kernel-default-devel package url. SUSE stores the primary package listing in XML.
        Once parsed, use the package URL to parse the kernel release and determine the kernel-devel*noarch package URL.
        '''


        # attempt to query for the repomd - bail out if 404
        try:
            repodb_url = self.get_repodb_url()
            repodb = get_url(repodb_url)
            if not repodb:
                return {}
        except requests.exceptions.RequestException:
            # traceback.print_exc()  # extremely verbose, uncomment if debugging
            return {}

        # write the repodb xml to a tempfile for parsing
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(repodb)
            tf.flush()
            kernel_default_devel_pkg_url = self.open_repo(tf.name)
            tf.close()  # delete the tempfile to free up memory

        # check to ensure a kernel_devel_pkg was found
        if not kernel_default_devel_pkg_url:
            return {}  # return an empty packages dict

        else:  # was able to find some packages
            packages = {}

            # parse out the kernel release from the url, faster than re-parsing the xml
            parsed_kernel_release = self.parse_kernel_release(kernel_default_devel_pkg_url)

            # add the kernel-devel-default package
            packages.setdefault(parsed_kernel_release, set()).add(self.base_url + kernel_default_devel_pkg_url)

            # also add the noarch kernel-devel pacakge
            # SUSE combines the kernel-default-devel package and kernel-devel*.noarch pacakge for compilation
            noarch_kernel_devel = self.build_kernel_devel_noarch_url(parsed_kernel_release)
            packages.setdefault(parsed_kernel_release, set()).add(noarch_kernel_devel)

            return packages
