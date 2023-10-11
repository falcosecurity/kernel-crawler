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

import logging
import json
import sys
import click

from .crawler import crawl_kernels, DISTROS

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
