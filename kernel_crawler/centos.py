from . import repo
from . import rpm

def v7_only(ver):
    return ver.startswith('7')


def v8_only(ver):
    return ver.startswith('8')


def v6_or_v7(ver):
    return ver.startswith('6') or ver.startswith('7')

class CentosMirror(repo.Distro):
    def __init__(self, arch):
        mirrors = [
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'os/' + arch + '/',  v7_only),
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'updates/' + arch + '/', v7_only),
            # CentOS 8 reached end-of-life at the end of 2021, so no point looking for it
            # rpm.RpmMirror('http://mirror.centos.org/centos/', 'BaseOS/' + arch + '/os/', v8_only),
            rpm.RpmMirror('http://linuxsoft.cern.ch/centos-vault/', 'os/' + arch + '/', v6_or_v7),
            rpm.RpmMirror('http://linuxsoft.cern.ch/centos-vault/', 'updates/' + arch + '/', v6_or_v7),
            rpm.RpmMirror('http://linuxsoft.cern.ch/centos-vault/', 'BaseOS/' + arch + '/os/', v8_only),
        ]
        super(CentosMirror, self).__init__(mirrors, arch)

    def to_driverkit_config(self, release, deps):
        return repo.DriverKitConfig(release, "centos")