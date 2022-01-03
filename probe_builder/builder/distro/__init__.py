from collections import namedtuple
from .centos import CentosBuilder
from .debian import DebianBuilder
from .flatcar import FlatcarBuilder
from .ubuntu import UbuntuBuilder


class Distro(namedtuple('Distro', 'distro builder_distro')):
    def builder(self):
        try:
            return DISTRO_BUILDERS[self.builder_distro]()
        except KeyError:
            raise ValueError('Unsupported builder distro {}'.format(self.builder_distro))


DISTRO_BUILDERS = {
    'centos': CentosBuilder,
    'debian': DebianBuilder,
    'flatcar': FlatcarBuilder,
    'ubuntu': UbuntuBuilder,
}
