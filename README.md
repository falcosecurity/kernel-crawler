# Falcosecurity kernel-crawler

It is a tool used to crawl supported kernels by multiple distros, and generate a [driverkit](https://github.com/falcosecurity/driverkit)-like config json.  
Output json can be found, for each supported architecture, under [kernels](/kernels) folder.  

A weekly [prow job](https://github.com/falcosecurity/test-infra/blob/master/config/jobs/update-kernels/update-kernels.yaml) will open a PR on this repo to update the json.  
As soon as the PR is merged and the json updated, another [prow job](https://github.com/falcosecurity/test-infra/blob/master/config/jobs/update-dbg/update-dbg.yaml) will create a PR on [test-infra](https://github.com/falcosecurity/test-infra) to generate the new Driverkit configs from the updated json.

Helper text and options:
```commandline
python __init__.py crawl --help
Usage: __init__.py crawl [OPTIONS]

Options:
    --distro [AmazonLinux|AmazonLinux2|AmazonLinux2022|CentOS|Debian|Fedora|Flatcar|Minikube|Oracle6|Oracle7|Oracle8|PhotonOS|Redhat|Ubuntu|*]
    --version TEXT
    --arch [x86_64|aarch64]
    --out_fmt [plain|json|driverkit]
    --image TEXT
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
| :exclamation: **Note**: Passing ```--image``` argument is supported with ```--distro=*``` |
|-------------------------------------------------------------------------------------------|

* Crawl Redhat kernels (specific to the container supplied), with no-formatted output:
```commandline
python __init__.py crawl --distro=Redhat --image=redhat/ubi8:registered
```