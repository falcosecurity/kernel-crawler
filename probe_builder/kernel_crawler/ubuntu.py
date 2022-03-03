from . import deb
from . import repo

class UbuntuMirror(repo.Distro):
    def __init__(self, arch='amd64'):
        if arch=='arm':
            arch='arm64'
        mirrors = [
            deb.DebMirror('http://mirrors.edge.kernel.org/ubuntu/', arch),
            deb.DebMirror('http://security.ubuntu.com/ubuntu/', arch),
            deb.DebMirror('http://ports.ubuntu.com/ubuntu-ports/', arch),
        ]
        super(UbuntuMirror, self).__init__(mirrors, arch)
