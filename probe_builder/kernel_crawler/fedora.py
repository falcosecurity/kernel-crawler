from probe_builder.kernel_crawler import repo, rpm


def repo_filter(version):
    """Don't bother testing ancient versions"""
    try:
        return int(version.rstrip('/')) >= 32
    except ValueError:
        return False


class FedoraMirror(repo.Distro):
    def __init__(self):
        mirrors = [
            rpm.RpmMirror('https://mirrors.kernel.org/fedora/releases/', 'Everything/x86_64/os/', repo_filter),
        ]
        super(FedoraMirror, self).__init__(mirrors)


