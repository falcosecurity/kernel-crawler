#!/usr/bin/env python
import sys

import click

from . import repo
from . import rpm
from probe_builder.kernel_crawler.download import get_url
from probe_builder.py23 import make_string


def get_al_repo(repo_root, repo_release):
    repo_pointer = repo_root + repo_release + "/mirror.list"
    resp = get_url(repo_pointer)
    return make_string(resp.splitlines()[0]).replace('$basearch', 'x86_64') + '/'


class AmazonLinux1Mirror(repo.Distro):
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
        with click.progressbar(
                self.AL1_REPOS, label='Checking repositories', file=sys.stderr, item_show_func=repo.to_s) as repos:
            for r in repos:
                repo_urls.add(get_al_repo("http://repo.us-east-1.amazonaws.com/", r))
        return [rpm.RpmRepository(url) for url in sorted(repo_urls)]


class AmazonLinux2Mirror(repo.Distro):
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
        with click.progressbar(
                self.AL2_REPOS, label='Checking repositories', file=sys.stderr, item_show_func=repo.to_s) as repos:
            for r in repos:
                repo_urls.add(get_al_repo("http://amazonlinux.us-east-1.amazonaws.com/2/", r + '/x86_64'))
        return [rpm.RpmRepository(url) for url in sorted(repo_urls)]
