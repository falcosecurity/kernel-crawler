from . import deb
from . import debian


class UbuntuMirror(debian.DebianLikeMirror):
    def __init__(self):
        mirrors = [
            deb.DebMirror('https://mirrors.edge.kernel.org/ubuntu/'),
            deb.DebMirror('http://security.ubuntu.com/ubuntu/'),
        ]
        super(UbuntuMirror, self).__init__(mirrors)
