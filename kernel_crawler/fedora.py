from . import repo, rpm

def repo_filter(version):
    """Don't bother testing ancient versions"""
    try:
        return int(version.rstrip('/')) >= 32
    except ValueError:
        return False


class FedoraMirror(repo.Distro):
    def __init__(self, arch):
        mirrors = [
            rpm.RpmMirror('https://mirrors.kernel.org/fedora/releases/', 'Everything/' + arch + '/os/', repo_filter),
            rpm.RpmMirror('https://mirrors.kernel.org/fedora/updates/', 'Everything/' + arch + '/', repo_filter),
        ]
        super(FedoraMirror, self).__init__(mirrors, arch)

    def to_driverkit_config(self, release, deps):
        for dep in deps:
            if dep.find("devel") != -1:
                return repo.DriverKitConfig(release, "fedora", dep)
