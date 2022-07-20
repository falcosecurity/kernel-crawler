from . import deb
from . import repo
from .debian import fixup_deb_arch
import re

class UbuntuMirror(repo.Distro):
    def __init__(self, arch):
        arch = fixup_deb_arch(arch)
        mirrors = [
            deb.DebMirror('http://mirrors.edge.kernel.org/ubuntu/', arch),
            deb.DebMirror('http://security.ubuntu.com/ubuntu/', arch),
            deb.DebMirror('http://ports.ubuntu.com/ubuntu-ports/', arch),
        ]
        super(UbuntuMirror, self).__init__(mirrors, arch)

    def to_driverkit_config(self, release, deps):
        dk_configs = {}
        krel, kver = release.split("/")
        for dep in deps:
            if dep.find("headers") != -1:
                # example: http://security.ubuntu.com/ubuntu/pool/main/l/linux-oracle/linux-headers-4.15.0-1087-oracle_4.15.0-1087.95_amd64.deb
                d = re.search(r"(\bl/linux(\-.+\/)?\b)", dep)
                if d is None:
                    continue

                d = d.group(0)
                target = "ubuntu"
                release = krel + d[7:len(d) - 1]

                val = dk_configs.get(target)
                if val is None:
                    headers = [dep]
                    dk_configs[target] = repo.DriverKitConfig(release, target, headers, kver)
                else:
                    # If already existent, just add the new url to the list of headers
                    val.headers.append(dep)
                    dk_configs[target] = val
        return dk_configs.values()