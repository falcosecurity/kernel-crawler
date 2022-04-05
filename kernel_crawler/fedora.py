from . import repo, rpm

def repo_filter(version):
    """Don't bother testing ancient versions"""
    try:
        return int(version.rstrip('/')) >= 32
    except ValueError:
        return False


class FedoraMirror(repo.Distro):
    def __init__(self, arch='x86_64'):
        if arch=='arm':
            arch='aarch64'
        mirrors = [
            rpm.RpmMirror('https://mirrors.kernel.org/fedora/releases/', 'Everything/' + arch + '/os/', repo_filter),
            rpm.RpmMirror('https://mirrors.kernel.org/fedora/updates/', 'Everything/' + arch + '/', repo_filter),
        ]
        super(FedoraMirror, self).__init__(mirrors, arch)


