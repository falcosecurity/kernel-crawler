from . import repo
from . import rpm


def v7_only(ver):
    return ver.startswith('7')


def v8_only(ver):
    return ver.startswith('8')


def v6_or_v7(ver):
    return ver.startswith('6') or ver.startswith('7')


class CentosMirror(repo.Distro):
    def __init__(self):
        mirrors = [
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'os/x86_64/', v7_only),
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'updates/x86_64/', v7_only),
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'BaseOS/x86_64/os/', v8_only),
            rpm.RpmMirror('https://vault.centos.org/', 'os/x86_64/', v6_or_v7),
            rpm.RpmMirror('https://vault.centos.org/', 'updates/x86_64/', v6_or_v7),
            rpm.RpmMirror('https://vault.centos.org/', 'BaseOS/x86_64/os/', v8_only),
        ]
        super(CentosMirror, self).__init__(mirrors)
