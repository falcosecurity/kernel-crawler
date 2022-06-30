import logging
import json
import sys
import click

from kernel_crawler import crawl_kernels, DISTROS, CONTAINER_DISTROS

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

class DistroContainerValidation(click.Option):
    def __init__(self, *args, **kwargs):
        self.required_if_distro:list = kwargs.pop("required_if_distro")

        assert self.required_if_distro, "'required_if_distro' parameter required"
        kwargs["help"] = (kwargs.get("help", "") + "Option is required when distro is " + ", ".join(self.required_if_distro) + ".").strip()
        super(DistroContainerValidation, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        current_opt:bool = self.name in opts
        tgt_distro:str = opts["distro"]
        for distro_opt in self.required_if_distro:
            if distro_opt == tgt_distro:
                if current_opt:
                    self.prompt = None
                else:
                    raise click.UsageError("Missing argument: '" + str(self.name) + "' is required with " + str(distro_opt) + " distro.")
            else:
                if current_opt:
                    raise click.UsageError("Invalid argument: '" + str(self.name) + "' is not required with " + tgt_distro + " distro.")
        return super(DistroContainerValidation, self).handle_parse_result(ctx, opts, args)

@click.command()
@click.option('--distro', type=click.Choice(sorted(list(DISTROS.keys()) + list(CONTAINER_DISTROS.keys())) + ['*'], case_sensitive=False))
@click.option('--version', required=False, default='')
@click.option('--arch', required=False, type=click.Choice(['x86_64', 'aarch64'], case_sensitive=False), default='x86_64')
@click.option('--out_fmt', required=False, type=click.Choice(['plain', 'json', 'driverkit'], case_sensitive=False),  default='plain')
@click.option('--container', cls=DistroContainerValidation, required_if_distro=["Redhat"])
def crawl(distro, version='', arch='', out_fmt='', container=''):
    res = crawl_kernels(distro, version, arch, container, out_fmt == 'driverkit')
    out_fmt = str.lower(out_fmt)
    if out_fmt == 'plain':
        for dist, ks in res.items():
            print('=== {} ==='.format(dist))
            for release, packages in ks.items():
                print('=== {} ==='.format(release))
                for pkg in packages:
                    print(' {}'.format(pkg))
    elif out_fmt == 'json':
        json_object = json.dumps(res, indent=2, cls=SetEncoder)
        print(json_object)
    elif out_fmt == 'driverkit':
        json_object = json.dumps(res, indent=2, default=vars)
        print(json_object)

cli.add_command(crawl, 'crawl')

if __name__ == '__main__':
    cli()
