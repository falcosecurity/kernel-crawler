from . import deb
from . import repo


class UbuntuMirror(repo.Distro):
    def __init__(self):
        mirrors = [
            deb.DebMirror('https://mirrors.edge.kernel.org/ubuntu/'),
            deb.DebMirror('http://security.ubuntu.com/ubuntu/'),
        ]
        super(UbuntuMirror, self).__init__(mirrors)
