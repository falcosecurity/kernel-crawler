import logging
import json
import sys
import click

from .crawler import crawl_kernels, DISTROS

logger = logging.getLogger(__name__)

def skip_exception_handler(type, value, tb):
    logger.exception("Uncaught exception: {0}".format(str(value))) 

def init_logging(debug, noexceptions):
    level = 'DEBUG' if debug else 'INFO'
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    handler.setLevel(level)
    logger.addHandler(handler)
    logger.debug("DEBUG logging enabled")
    if noexceptions:
        # Install exception handler that just logs
        sys.excepthook = skip_exception_handler

@click.group()
@click.option('--debug', required=False, is_flag=True, default=False, help="Enable debug logs.")
@click.option('--noexceptions', required=False, is_flag=True, default=False, help="Skip exceptions, logging them.")
def cli(debug, noexceptions):
    init_logging(debug, noexceptions)

class DistroImageValidation(click.Option):
    def __init__(self, *args, **kwargs):
        self.required_if_distro:list = kwargs.pop("required_if_distro")

        assert self.required_if_distro, "'required_if_distro' parameter required"
        kwargs["help"] = (kwargs.get("help", "") + "Option is required when distro is " + ", ".join(self.required_if_distro) + ".").strip()
        super(DistroImageValidation, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        current_opt:bool = self.name in opts
        tgt_distro:str = opts["distro"]
        for distro_opt in self.required_if_distro:
            if distro_opt.casefold() == tgt_distro.casefold():
                if current_opt:
                    self.prompt = None
                else:
                    raise click.UsageError("Missing argument: '" + str(self.name) + "' is required with " + str(distro_opt) + " distro.")
        return super(DistroImageValidation, self).handle_parse_result(ctx, opts, args)

@click.command()
@click.option('--distro', type=click.Choice(sorted(list(DISTROS.keys())) + ['*'], case_sensitive=True))
@click.option('--version', required=False, default='')
@click.option('--arch', required=False, type=click.Choice(['x86_64', 'aarch64'], case_sensitive=True), default='x86_64')
@click.option('--image', cls=DistroImageValidation, required_if_distro=["Redhat"], multiple=True)
def crawl(distro, version='', arch='', image=''):
    res = crawl_kernels(distro, version, arch, image)
    json_object = json.dumps(res, indent=2, default=vars)
    print(json_object)

cli.add_command(crawl, 'crawl')

if __name__ == '__main__':
    cli()
