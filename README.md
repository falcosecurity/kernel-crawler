# Falcosecurity kernel-crawler

[![Update list of kernels weekly](https://github.com/falcosecurity/kernel-crawler/actions/workflows/update_kernels.yaml/badge.svg)](https://github.com/falcosecurity/kernel-crawler/actions/workflows/update_kernels.yaml)

Helper text and options:
```commandline
python __init__.py crawl --help
Usage: __init__.py crawl [OPTIONS]

Options:
    --distro [AmazonLinux|AmazonLinux2|AmazonLinux2022|CentOS|Debian|Fedora|Flatcar|Oracle6|Oracle7|Oracle8|PhotonOS|Ubuntu|*]
    --version TEXT
    --arch [x86_64|aarch64]
    --out_fmt [plain|json|driverkit]
    --help
```
## Examples

* Crawl amazonlinux2 kernels, with no-formatted output:
```commandline
python __init__.py crawl --distro=AmazonLinux2
```

* Crawl ubuntu kernels, with [driverkit](https://github.com/falcosecurity/driverkit) config-like output:
```commandline
python __init__.py crawl --distro=Ubuntu --out_fmt=driverkit
```

* Crawl all supported distros kernels, with json output:
```commandline
python __init__.py crawl --distro=* --out_fmt=json
```
