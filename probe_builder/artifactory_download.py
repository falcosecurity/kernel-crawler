#!/usr/bin/env python

from __future__ import print_function

import click
import requests
import json

from probe_builder.context import DownloadConfig
from probe_builder.builder.distro.base_builder import to_s
from probe_builder.kernel_crawler.download import download_file


def list_artifactory_rpm(url, key, repo_name):
    req = {'repo': repo_name}
    req = 'items.find({})'.format(json.dumps(req))
    resp = requests.post(url + '/api/search/aql', data=req, headers={
        'Content-Type': 'text/plain',
        'X-JFrog-Art-Api': key,
    })

    resp.raise_for_status()
    resp = resp.json()
    for pkg in resp['results']:
        if pkg['name'].endswith('.rpm'):
            yield pkg['name']


def download_artifactory_rpm(url, key, repo_name, pkgs):
    download_config = DownloadConfig(1, None, 1, {
        'X-JFrog-Art-Api': key
    })

    with click.progressbar(pkgs, item_show_func=to_s) as pkgs:
        for pkg in pkgs:
            pkg_url = '{}/{}/{}'.format(url, repo_name, pkg)
            download_file(pkg_url, pkg, download_config)


@click.group()
@click.pass_context
@click.option('--url')
@click.option('--key')
@click.option('--repo')
def cli(ctx, url, key, repo):
    ctx.ensure_object(dict)
    ctx.obj['url'] = url
    ctx.obj['key'] = key
    ctx.obj['repo'] = repo


@click.command()
@click.pass_obj
def cli_list(obj):
    for pkg in list_artifactory_rpm(obj['url'], obj['key'], obj['repo']):
        print(pkg)


@click.command()
@click.pass_obj
def cli_download(obj):
    rpms = list(list_artifactory_rpm(obj['url'], obj['key'], obj['repo']))
    download_artifactory_rpm(obj['url'], obj['key'], obj['repo'], rpms)


cli.add_command(cli_list, 'list')
cli.add_command(cli_download, 'download')

if __name__ == '__main__':
    cli()
