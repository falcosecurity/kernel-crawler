import os

import requests
from lxml import html

from probe_builder.kernel_crawler.repo import Repository, Distro


class FlatcarRepository(Repository):
    def __init__(self, base_url):
        self.base_url = base_url

    def get_package_tree(self, version=''):
        release = os.path.basename(self.base_url.rstrip('/'))
        if version not in release:
            return {}
        dev_container = os.path.join(self.base_url, 'flatcar_developer_container.bin.bz2')
        return {release: [dev_container]}

    def __str__(self):
        return self.base_url


class FlatcarMirror(Distro):
    CHANNELS = ['stable', 'beta', 'alpha']

    def __init__(self):
        mirrors = ['https://{}.release.flatcar-linux.net/amd64-usr/'.format(channel) for channel in self.CHANNELS]
        super(FlatcarMirror, self).__init__(mirrors)

    def scan_repo(self, base_url):
        dists = requests.get(base_url)
        dists.raise_for_status()
        dists = dists.content
        doc = html.fromstring(dists, base_url)
        dists = doc.xpath('/html/body//a[not(@href="../")]/@href')
        return [FlatcarRepository('{}{}'.format(base_url, dist.lstrip('./'))) for dist in dists
                if dist.endswith('/')
                and dist.startswith('./')
                and 'current' not in dist
                and '-' not in dist
                ]

    def list_repos(self):
        repos = []
        for repo in self.mirrors:
            repos.extend(self.scan_repo(repo))
        return repos
