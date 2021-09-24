#!/usr/bin/env python
#
# Copyright (C) 2013-2018 Draios Inc dba Sysdig.
#
# This file is part of sysdig .
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# This script is used to:
# - scan a well-known distribution mirror for kernel packages
# - get all the packages' dependencies
# - print the URLs for all packages (kernels and dependencies)
#
# We unfortunately still need some heuristics to find the right
# packages but at least we get the dependencies cleanly.
# In theory we could inspect the package content lists, but
# that ends up being very slow.
#
# In the code, we have a few parallel class hierarchies, all
# based in an abstract interface, implemented by concrete
# RPM/DEB classes:
# - a Repository, as defined by having a single package database
# - a mirror, as defined by being a single http(s) server
# - a distribution, i.e. a collection of mirrors
#
# Please note that we don't have a notion of a distribution version
# in the abstract interface.
#
# Packages from different repositories are handled differently
# for rpm/deb systems:
# - rpm-based repos are completely independent of each other
#   (since the repositories are generally self-contained, even
#   for e.g. updates)
# - deb-based mirrors get their contents regrouped along `dist` lines
#   (e.g. all Ubuntu Xenial packages are kept in one map, independent
#   of whether they're coming from security, updates, backports etc.)
#
#   This is required for two reasons:
#   - package names are supposed to be unique in a distro (and they're
#     not unique across different distributions) so otherwise we'd get
#     wrong URLs (from the same package but a different distro)
#   - the repositories aren't self contained, e.g. security repos
#     may depend on kbuild packages from the main repo

from __future__ import print_function
import re
import tempfile

from lxml import etree, html
import zlib
import bz2
import sys
import sqlite3

# --- disable ipv6 ---
import socket

origGetAddrInfo = socket.getaddrinfo


def getaddrinfo_ipv4only(host, port, family=0, socktype=0, proto=0, flags=0):
    return origGetAddrInfo(host, port, socket.AF_INET, socktype, proto, flags)


# replace the original socket.getaddrinfo by our version
socket.getaddrinfo = getaddrinfo_ipv4only
# ---

# --- http helpers ---

try:
    # noinspection PyCompatibility
    from urllib2 import urlopen, unquote
except ImportError:
    # noinspection PyCompatibility
    from urllib.request import urlopen
    # noinspection PyCompatibility
    from urllib.parse import unquote

try:
    # noinspection PyCompatibility
    from lzma import decompress as lzma_decompress
except ImportError:
    try:
        from backports.lzma import decompress as lzma_decompress
    except ImportError:
        def lzma_decompress(content):
            raise NotImplementedError("LZMA compression not supported, install backports.lzma")


def get_url(url):
    print('Retrieving {}'.format(url), file=sys.stderr)
    resp = urlopen(url)
    if url.endswith('.gz'):
        return zlib.decompress(resp.read(), 47)
    elif url.endswith('.xz'):
        return lzma_decompress(resp.read())
    elif url.endswith('.bz2'):
        return bz2.decompress(resp.read())
    else:
        return resp.read()


def get_first_of(urls):
    last_exc = Exception('Empty url list')
    for url in urls:
        try:
            return get_url(url)
        except Exception as exc:
            last_exc = exc
    raise last_exc


def check_url(url):
    resp = urlopen(url)
    return resp.getcode() == 200


def check_any(urls):
    return any(check_url(url) for url in urls)


# --- generic repo stuff ---


class Repository(object):
    # return a map of {kernel_package_name => [dependencies]}
    # if version is specified, limit only to the specified version
    def get_package_tree(self, version=''):
        raise NotImplementedError

    # return true if the repository exists
    # it might not if we're guessing the URL based on heuristics
    def is_valid(self):
        raise NotImplementedError

    # a textual representation of the repository, e.g. its URL
    def __str__(self):
        raise NotImplementedError


class Mirror(object):
    # list repositories located on this http(s) server
    def list_repos(self):
        raise NotImplementedError

    # collect the results of `get_package_tree()` of all repos
    # in this mirror
    def get_package_tree(self, version=''):
        packages = {}
        repos = self.list_repos()
        for repo in repos:
            for release, dependencies in repo.get_package_tree(version).items():
                packages.setdefault(release, set()).update(dependencies)
        return packages

    # flatten the hierarchy from `get_package_tree` and just return
    # the urls to all packages
    #
    # this should become unnecessary once we teach the builder
    # to use the dependency information instead of guessing
    # the relations between packages itself
    def get_package_urls(self, version=''):
        urls = []
        for dependencies in self.get_package_tree(version).values():
            urls.extend(dependencies)
        return urls


class MultiMirror(Mirror):
    def __init__(self, mirrors):
        self.mirrors = mirrors

    # combine the list of repositories from all the mirrors
    # for this distribution
    def list_repos(self):
        repos = []
        for mirror in self.mirrors:
            repos.extend(mirror.list_repos())
        return repos


# --- Debian-like repos ---


class DebRepository(Repository):

    # repo_base is e.g. https://mirrors.edge.kernel.org/debian/
    # repo_name is e.g. dists/bookworm/main/binary-amd64/
    # together they form the url to the directory containing Packages.gz
    # while repo_base itself is prepended to the `Filename` field
    # from the package metadata to get the full url to the package
    def __init__(self, repo_base, repo_name):
        self.repo_base = repo_base
        self.repo_name = repo_name

        # guess the distro name (like `xenial` or `bookworm`)
        # used to group packages by distro instead of by repo
        dist = repo_name.replace('dists/', '').split('/')[0].split('-')[0]
        self.dist = dist

    def __str__(self):
        return self.repo_base + self.repo_name

    def is_valid(self):
        return check_any([
            self.repo_base + self.repo_name + '/Packages.gz',
            self.repo_base + self.repo_name + '/Packages.xz',
        ])

    # parse the Debian repo database
    # return a map of package_name => { version, dependencies, filename }
    @classmethod
    def scan_packages(cls, stream):
        """
        Parse a Packages file into individual packages metadata.
        """
        current_package = {}
        packages = {}
        for line in stream:
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

    # what is a Debian kernel package?
    # we want to consider linux-*-x.y.z packages, except for
    # - linux-*-dbg,
    # - linux-modules-extra-*,
    # - linux-source-*,
    # - linux-tools-*
    # and also linux-kbuild-x.y packages
    #
    # since the kernel packages depend on all sorts of things
    # (like e.g. coreutils), we only limit the dependencies
    # to actual kernel packages or we'd end up with most of
    # a Debian system
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

    # given a package, find its dependencies recursively
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
            # the linux-image packages tend to depend on a lot of userspace
            # packages (needed to e.g. install the kernel on a live system)
            # but not for our purposes so we only filter for kernel packages
            if dep in packages:
                if dep not in dependencies:
                    if dep not in cache:
                        dependencies |= {dep}
                        deps = {dep}
                        deps |= cls.transitive_dependencies(packages, dep, dependencies, level + 1, cache)
                        cache[dep] = deps
                    dependencies |= cache[dep]
            else:
                # make sure we have a complete list of packages
                # (pieced together from multiple repos if needed)
                raise RuntimeError("{} not in package list".format(dep))
        return dependencies

    # the entry point into the transitive_dependencies recursive method
    # returns the set of URLs needed for `pkg` and its dependencies
    @classmethod
    def get_package_deps(cls, packages, pkg):
        all_deps = set()
        if not cls.is_kernel_package(pkg):
            return set()
        for dep in cls.filter_kernel_packages(cls.transitive_dependencies(packages, pkg)):
            all_deps.add(packages[dep]['URL'])
        return all_deps

    # find a list of kernel packages
    # since the names vary across distros and releases,
    # we do a two step process
    # first, find the headers package (at least that part is consistent
    # and the packages are called linux-headers-<version>)
    # then, check for the first of:
    # - linux-modules-<version>
    # - linux-image-<version>
    # - linux-image-<version>-unsigned>
    #
    # at some point the linux-image* packages switched to only
    # shipping the kernel image (vmlinuz) itself plus a dependency
    # on linux-modules. We only need /boot/config-<version> from
    # the binary package, so prefer the modules package if it exists
    def get_package_list(self, deps, package_filter):
        kernel_packages = []
        for p in deps.keys():
            if not p.startswith('linux-headers-'):
                continue
            # historically, we haven't built these variants
            # and there's a ton of them. Leave them disabled,
            # we can enable them when we need to
            if '-cloud' in p:
                continue
            if '-rt' in p:
                continue
            if '-lowlatency' in p:
                continue
            if '-azure' in p:
                continue
            if '-oem' in p:
                continue
            if '-gcp' in p:
                continue
            if '-gke' in p:
                continue
            if '-oracle' in p:
                continue
            if '-kvm' in p:
                continue
            # skip backported kernels (again, to match historic behavior
            # and to avoid an explosion in the number of built probes)
            if '-lts-' in deps[p]['URL']:
                continue
            if '-hwe' in deps[p]['URL']:
                continue
            release = p.replace('linux-headers-', '')
            candidates = ['linux-modules-{}', 'linux-image-{}', 'linux-image-{}-unsigned']
            for c in candidates:
                candidate = c.format(release)
                if candidate in deps:
                    kernel_packages.append(p)
                    kernel_packages.append(candidate)
                    break

        if not package_filter:
            return kernel_packages

        # apply the version filter
        kernel_packages = set(kernel_packages)
        if package_filter in deps:
            return [package_filter]
        elif 'linux-modules-{}'.format(package_filter) in kernel_packages and 'linux-headers-{}'.format(
                package_filter) in deps:
            return ['linux-modules-{}'.format(package_filter), 'linux-headers-{}'.format(package_filter)]
        elif 'linux-image-{}'.format(package_filter) in kernel_packages and 'linux-headers-{}'.format(
                package_filter) in deps:
            return ['linux-image-{}'.format(package_filter), 'linux-headers-{}'.format(package_filter)]
        else:
            return [k for k in kernel_packages if package_filter in k]

    # download and parse the package database
    def get_raw_package_db(self):
        try:
            repo_packages = get_first_of([
                self.repo_base + self.repo_name + '/Packages.gz',
                self.repo_base + self.repo_name + '/Packages.xz',
            ])
        except:
            return {}

        repo_packages = repo_packages.splitlines(True)
        packages = self.scan_packages(repo_packages)
        for name, details in packages.items():
            details['URL'] = self.repo_base + details['Filename']
        return {self.dist: packages}

    @classmethod
    def build_package_tree(cls, packages, package_list):
        deps = {}
        for pkg in package_list:
            pv = packages[pkg]['Version']
            # we unpack e.g. 4.15.0-140.144 to 4.15.0-140/144
            # make the probe builder's life a little bit easier
            # (when we use more of the kernel crawler than just
            # the raw urls)
            m = cls.KERNEL_RELEASE_UPDATE.match(pv)
            if m:
                pv = '{}/{}'.format(m.group(1), m.group(2))
            deps.setdefault(pv, set()).update(cls.get_package_deps(packages, pkg))
        for pkg, dep_list in deps.items():
            have_headers = False
            for dep in dep_list:
                if 'linux-headers' in dep:
                    have_headers = True
            if not have_headers:
                del deps[pkg]
        return deps

    def get_package_tree(self, version=''):
        packages = self.get_raw_package_db()
        package_tree = {}
        for dist, dist_packages in packages.items():
            package_list = self.get_package_list(dist_packages, version)
            for pkg, deps in self.build_package_tree(dist_packages, package_list):
                package_tree[dist + ':' + pkg] = deps
        return package_tree


class DebMirror(Mirror):

    def __init__(self, base_url, repo_filter=None):
        # scan the http server at `base_url` to find repos inside
        # only consider repos (http links) matching the repo filter
        # (matches everything by default)
        self.base_url = base_url
        if repo_filter is None:
            repo_filter = lambda _: True
        self.repo_filter = repo_filter

    def scan_repo(self, dist):
        # find the components in a repository
        # we only care about main, updates and updates/main
        # not about e.g. contrib or non-free
        #
        # unfortunately, naming isn't very consistent
        # so e.g. some repos inside updates/ have an updates/main
        # component. We strip that out if we see a double updates/
        # in the url
        repos = {}
        all_comps = set()
        release = get_url(self.base_url + dist + 'Release')
        for line in release.splitlines(False):
            if line.startswith('Components: '):
                for comp in line.split(None)[1:]:
                    if comp in ('main', 'updates', 'updates/main'):
                        if dist.endswith('updates/') and comp.startswith('updates/'):
                            comp = comp.replace('updates/', '')
                        all_comps.add(comp)
                break
        for comp in all_comps:
            url = dist + comp + '/binary-amd64/'
            repos[url] = DebRepository(self.base_url, url)
        return repos

    def list_repos(self):
        dists_url = self.base_url + 'dists/'
        dists = get_url(dists_url)
        doc = html.fromstring(dists, dists_url)
        dists = [dist for dist in doc.xpath('/html/body//a[not(@href="../")]/@href')
                 if dist.endswith('/')
                 and not dist.startswith('/')
                 and not dist.startswith('?')
                 and not dist.startswith('http')
                 and self.repo_filter(dist)
                 ]

        repos = {}
        for dist in dists:
            # unfortunately, there's no way to know if there's
            # an updates/ subdirectory from the top level
            try:
                repos.update(self.scan_repo('dists/{}'.format(dist)))
            except:
                pass
            try:
                repos.update(self.scan_repo('dists/{}updates/'.format(dist)))
            except:
                pass

        return sorted(repos.values())


class DebianLikeMirror(MultiMirror):

    # since we need to group the Debian packages along dist lines, not along repo lines,
    # we override the `get_package_tree` method to work nicely with the modified
    # schema of values returned from DebRepository.build_package_tree
    # until we use the dependency information in the probe builder itself,
    # the key used (dist :: release) is arbitrary. When we start using the metadata,
    # we might want to collapse releases across different dists here, so that
    # packages[release] contains the dependencies for all dists and let the probe builder
    # sort it out
    def get_package_tree(self, version=''):
        all_packages = {}
        all_kernel_packages = {}
        packages = {}
        repos = self.list_repos()
        for repository in repos:
            repo_packages = repository.get_raw_package_db()
            for dist, dist_packages in repo_packages.items():
                all_packages.setdefault(dist, {}).update(dist_packages)
                kernel_packages = repository.get_package_list(dist_packages, version)
                all_kernel_packages.setdefault(dist, []).extend(kernel_packages)

        for dist, dist_packages in all_packages.items():
            dist_kernel_packages = all_kernel_packages.get(dist, [])

            for release, dependencies in DebRepository.build_package_tree(dist_packages, dist_kernel_packages).items():
                if release not in packages:
                    packages[dist + '::' + release] = set(dependencies)
        return packages


class DebianMirror(DebianLikeMirror):
    @classmethod
    def repo_filter(cls, dist):
        # use the code names (bookworm etc.), not stable/testing/unstable aliases
        # or version numbers
        return 'stable' not in dist and 'testing' not in dist and not dist.startswith('Debian')

    def __init__(self):
        mirrors = [
            DebMirror('https://mirrors.edge.kernel.org/debian/', self.repo_filter),
            DebMirror('http://security.debian.org/', self.repo_filter),
        ]
        super(DebianMirror, self).__init__(mirrors)


class UbuntuMirror(DebianLikeMirror):
    def __init__(self):
        mirrors = [
            DebMirror('https://mirrors.edge.kernel.org/ubuntu/'),
            DebMirror('http://security.ubuntu.com/ubuntu/'),
        ]
        super(UbuntuMirror, self).__init__(mirrors)


# --- RPM repos ---


class RpmRepository(Repository):
    def __init__(self, base_url):
        self.base_url = base_url

    def __str__(self):
        return self.base_url

    def is_valid(self):
        return check_url(self.base_url + 'repodata/repomd.xml')

    @classmethod
    def get_loc_by_xpath(cls, text, expr):
        e = etree.fromstring(text)
        loc = e.xpath(expr, namespaces={
            'common': 'http://linux.duke.edu/metadata/common',
            'repo': 'http://linux.duke.edu/metadata/repo',
            'rpm': 'http://linux.duke.edu/metadata/rpm'
        })
        return loc[0]

    @classmethod
    def kernel_package_query(cls):
        # what is a kernel package? CentOS like distros generally stick to
        # kernel and kernel-devel, but e.g. PhotonOS uses linux{,-devel}
        # so make this a class method that subclasses can override
        return '''name IN ('kernel', 'kernel-devel')'''

    @classmethod
    def build_base_query(cls, version=''):
        # based on whether we have a filter or not, build the query for the base case
        # i.e. "find all kernel packages we're interested in"
        base_query = '''SELECT version || '-' || release || '.' || arch, pkgkey FROM packages WHERE {}'''.format(
            cls.kernel_package_query())
        if not version:
            return base_query, ()
        else:
            return base_query + ''' AND (version = ? OR version || '-' || "release" = ?)''', (version, version)

    @classmethod
    def parse_repo_db(cls, repo_db, version=''):
        db = sqlite3.connect(repo_db)
        cursor = db.cursor()

        # we can do a recursive SQL query to find all packages
        # and their (transitive) dependencies in one shot. Behold.
        base_query, args = cls.build_base_query(version)
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

    def get_repodb_url(self):
        repomd = get_url(self.base_url + 'repodata/repomd.xml')
        pkglist_url = self.get_loc_by_xpath(repomd, '//repo:repomd/repo:data[@type="primary_db"]/repo:location/@href')
        return self.base_url + pkglist_url

    def get_package_tree(self, version=''):
        # download the sqlite database and query it
        packages = {}
        try:
            repodb_url = self.get_repodb_url()
            repodb = get_url(repodb_url)
        except:
            return {}
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(repodb)
            tf.flush()
            for pkg in self.parse_repo_db(tf.name, version):
                version, url = pkg
                packages.setdefault(version, set()).add(self.base_url + url)
        return packages


class RpmMirror(Mirror):

    # scan the http server at `base_url` to find repos inside
    # only consider repos (http links) matching the repo filter
    # (matches everything by default)
    #
    # the variant is the distro-specific bit inside a particular dist
    def __init__(self, base_url, variant, repo_filter=None):
        self.base_url = base_url
        self.variant = variant
        if repo_filter is None:
            repo_filter = lambda _: True
        self.repo_filter = repo_filter

    def list_repos(self):
        dists = get_url(self.base_url)
        doc = html.fromstring(dists, self.base_url)
        dists = doc.xpath('/html/body//a[not(@href="../")]/@href')
        return [RpmRepository('{}{}{}'.format(self.base_url, dist, self.variant)) for dist in dists
                if dist.endswith('/')
                and not dist.startswith('/')
                and not dist.startswith('?')
                and not dist.startswith('http')
                and self.repo_filter(dist)
                ]


class CentosMirror(MultiMirror):
    def __init__(self):
        mirrors = [
            RpmMirror('http://mirror.centos.org/centos/', 'os/x86_64/', lambda ver: ver.startswith('7')),
            RpmMirror('http://mirror.centos.org/centos/', 'updates/x86_64/', lambda ver: ver.startswith('7')),
            RpmMirror('http://mirror.centos.org/centos/', 'BaseOS/x86_64/os/', lambda ver: ver.startswith('8')),
            RpmMirror('https://vault.centos.org/', 'os/x86_64/',
                      lambda ver: ver.startswith('6') or ver.startswith('7')),
            RpmMirror('https://vault.centos.org/', 'updates/x86_64/',
                      lambda ver: ver.startswith('6') or ver.startswith('7')),
            RpmMirror('https://vault.centos.org/', 'BaseOS/x86_64/os/', lambda ver: ver.startswith('8')),
        ]
        super(CentosMirror, self).__init__(mirrors)


class FedoraMirror(MultiMirror):
    @classmethod
    def repo_filter(cls, version):
        """Don't bother testing ancient versions"""
        try:
            return int(version.rstrip('/')) >= 32
        except ValueError:
            return False

    def __init__(self):
        mirrors = [
            RpmMirror('https://mirrors.kernel.org/fedora/releases/', 'Everything/x86_64/os/', self.repo_filter),
        ]
        super(FedoraMirror, self).__init__(mirrors)


def get_al_repo(repo_root, repo_release):
    repo_pointer = repo_root + repo_release + "/mirror.list"
    resp = get_url(repo_pointer)
    return resp.splitlines()[0].replace('$basearch', 'x86_64') + '/'


class AmazonLinux1Mirror(MultiMirror):
    AL1_REPOS = [
        'latest/updates',
        'latest/main',
        '2017.03/updates',
        '2017.03/main',
        '2017.09/updates',
        '2017.09/main',
        '2018.03/updates',
        '2018.03/main',
    ]

    def __init__(self):
        super(AmazonLinux1Mirror, self).__init__([])

    def list_repos(self):
        repo_urls = set()
        for r in self.AL1_REPOS:
            repo_urls.add(get_al_repo("http://repo.us-east-1.amazonaws.com/", r))
        return [RpmRepository(url) for url in sorted(repo_urls)]


class AmazonLinux2Mirror(MultiMirror):
    AL2_REPOS = [
        'core/2.0',
        'core/latest',
        'extras/kernel-5.4/latest',
        'extras/kernel-5.10/latest',
    ]

    def __init__(self):
        super(AmazonLinux2Mirror, self).__init__([])

    def list_repos(self):
        repo_urls = set()
        for r in self.AL2_REPOS:
            repo_urls.add(get_al_repo("http://amazonlinux.us-east-1.amazonaws.com/2/", r + '/x86_64'))
        return [RpmRepository(url) for url in sorted(repo_urls)]


class PhotonOsRepository(RpmRepository):
    @classmethod
    def kernel_package_query(cls):
        # we exclude `esx` kernels because they don't support CONFIG_TRACEPOINTS
        # see https://github.com/vmware/photon/issues/1223
        return '''((name = 'linux' OR name LIKE 'linux-%devel%') AND name NOT LIKE '%esx%')'''


class PhotonOsMirror(MultiMirror):
    PHOTON_OS_VERSIONS = [
        ('3.0', '_release'),
        ('3.0', '_updates'),
        ('4.0', ''),
        ('4.0', '_release'),
        ('4.0', '_updates'),
    ]

    def __init__(self):
        super(PhotonOsMirror, self).__init__([])

    def list_repos(self):
        return [
            PhotonOsRepository(
                'https://packages.vmware.com/photon/{v}/photon{r}_{v}_x86_64/'.format(v=version, r=repo_tag))
            for version, repo_tag in self.PHOTON_OS_VERSIONS]


class OracleRepository(RpmRepository):
    @classmethod
    def kernel_package_query(cls):
        return '''(name IN ('kernel', 'kernel-devel', 'kernel-uek', 'kernel-uek-devel') AND arch = 'x86_64')'''


class OracleMirror(MultiMirror):
    REPOS = []

    def __init__(self):
        super(OracleMirror, self).__init__([])

    def list_repos(self):
        return [OracleRepository(url) for url in self.REPOS]


class Oracle6Mirror(OracleMirror):
    REPOS = [
        'http://yum.oracle.com/repo/OracleLinux/OL6/latest/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL6/MODRHCK/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL6/UEKR4/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL6/UEKR3/latest/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL6/UEK/latest/x86_64/',
    ]


class Oracle7Mirror(OracleMirror):
    REPOS = [
        'http://yum.oracle.com/repo/OracleLinux/OL7/latest/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL7/MODRHCK/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR6/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR5/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR4/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR3/x86_64/',
    ]


class Oracle8Mirror(OracleMirror):
    REPOS = [
        'http://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/x86_64/',
        'http://yum.oracle.com/repo/OracleLinux/OL8/UEKR6/x86_64/',
    ]


# --- Dummy empty repos, for compatibility ---


class EmptyMirror(object):
    @staticmethod
    def get_package_urls(version=''):
        return []


DISTROS = {
    'Debian': DebianMirror,
    'Ubuntu': UbuntuMirror,

    'CentOS': CentosMirror,
    'Fedora': FedoraMirror,

    'AmazonLinux': AmazonLinux1Mirror,
    'AmazonLinux2': AmazonLinux2Mirror,

    'PhotonOS': PhotonOsMirror,

    'OracleLinux6': Oracle6Mirror,
    'OracleLinux7': Oracle7Mirror,
    'OracleLinux8': Oracle8Mirror,

    'CoreOS': EmptyMirror,
    'Fedora-Atomic': EmptyMirror,
}


def usage():
    print('Supported distributions:', file=sys.stderr)
    for distro in sorted(DISTROS.keys()):
        print(distro, file=sys.stderr)


def main():
    try:
        distro_cls = DISTROS[sys.argv[1]]
    except IndexError:
        print('Usage: kernel-crawler.py DISTRO [VERSION]', file=sys.stderr)
        usage()
        sys.exit(1)
    except KeyError:
        print('Unsupported distribution {}'.format(sys.argv[1]), file=sys.stderr)
        usage()
        sys.exit(1)

    try:
        version = sys.argv[2]
    except IndexError:
        version = ''

    distro = distro_cls()
    for url in distro.get_package_urls(version):
        print(url)


if __name__ == '__main__':
    main()
