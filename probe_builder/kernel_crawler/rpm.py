#!/usr/bin/env python
from __future__ import print_function

import requests
from lxml import etree, html
import sqlite3
import tempfile

from . import repo
from probe_builder.kernel_crawler.download import get_url

try:
    import lzma
except ImportError:
    from backports import lzma


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
        return loc[0]

    @classmethod
    def kernel_package_query(cls):
        return '''name IN ('kernel', 'kernel-devel')'''

    @classmethod
    def build_base_query(cls, version=''):
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
        packages = {}
        try:
            repodb_url = self.get_repodb_url()
            repodb = get_url(repodb_url)
        except requests.HTTPError:
            return {}
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(repodb)
            tf.flush()
            for pkg in self.parse_repo_db(tf.name, version):
                version, url = pkg
                packages.setdefault(version, set()).add(self.base_url + url)
        return packages


class RpmMirror(repo.Mirror):

    def __init__(self, base_url, variant, repo_filter=None):
        self.base_url = base_url
        self.variant = variant
        if repo_filter is None:
            repo_filter = lambda _: True
        self.repo_filter = repo_filter

    def __str__(self):
        return self.base_url

    def list_repos(self):
        dists = requests.get(self.base_url)
        dists.raise_for_status()
        dists = dists.content
        doc = html.fromstring(dists, self.base_url)
        dists = doc.xpath('/html/body//a[not(@href="../")]/@href')
        return [RpmRepository('{}{}{}'.format(self.base_url, dist, self.variant)) for dist in dists
                if dist.endswith('/')
                and not dist.startswith('/')
                and not dist.startswith('?')
                and not dist.startswith('http')
                and self.repo_filter(dist)
                ]
