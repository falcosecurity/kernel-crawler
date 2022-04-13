import logging
import json
import sys
import click

from kernel_crawler import crawl_kernels, DISTROS

logger = logging.getLogger(__name__)

def init_logging(debug):
    level = 'DEBUG' if debug else 'INFO'
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    handler.setLevel(level)
    logger.addHandler(handler)
    logger.debug("DEBUG logging enabled")

@click.group()
@click.option('--debug/--no-debug')
def cli(debug):
    init_logging(debug)

class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

@click.command()
@click.option('--distro', type=click.Choice(sorted(DISTROS.keys()) + ['*'], case_sensitive=False))
@click.option('--version', required=False, default='')
@click.option('--arch', required=False, type=click.Choice(['x86_64', 'aarch64'], case_sensitive=False), default='x86_64')
@click.option('--out_fmt', required=False, type=click.Choice(['plain', 'json', 'driverkit'], case_sensitive=False),  default='plain')
def crawl(distro, version='', arch='', out_fmt=0):
    res = crawl_kernels(distro, version, arch, out_fmt == 'driverkit')
    match out_fmt:
        case 'plain':
            for dist, ks in res.items():
                print('=== {} ==='.format(dist))
                for release, packages in ks.items():
                    print('=== {} ==='.format(release))
                    for pkg in packages:
                        print(' {}'.format(pkg))
        case 'json':
            json_object = json.dumps(res, indent=2, cls=SetEncoder)
            print(json_object)
        case 'driverkit':
            json_object = json.dumps(res, indent=2, default=vars)
            print(json_object)

cli.add_command(crawl, 'crawl')

if __name__ == '__main__':
    cli()
