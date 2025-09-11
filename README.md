# Falcosecurity kernel-crawler
 
 [![Falco Infra Repository](https://github.com/falcosecurity/evolution/blob/main/repos/badges/falco-infra-blue.svg)](https://github.com/falcosecurity/evolution/blob/main/REPOSITORIES.md#infra-scope) [![Incubating](https://img.shields.io/badge/status-incubating-orange?style=for-the-badge)](https://github.com/falcosecurity/evolution/blob/main/REPOSITORIES.md#incubating) [![License](https://img.shields.io/github/license/falcosecurity/kernel-crawler?style=for-the-badge)](./LICENSE)
 
[![Latest](https://img.shields.io/github/v/release/falcosecurity/kernel-crawler?style=for-the-badge)](https://github.com/falcosecurity/kernel-crawler/releases/latest)
![Architectures](https://img.shields.io/badge/ARCHS-x86__64%7Caarch64-blueviolet?style=for-the-badge)
 
It is a tool used to crawl supported kernels by multiple distros, and generate a [driverkit](https://github.com/falcosecurity/driverkit)-like config json.  
Output json can be found, for each supported architecture, on gh pages: https://falcosecurity.github.io/kernel-crawler/:  
* [aarch64](https://falcosecurity.github.io/kernel-crawler/aarch64/list.json)
* [x86_64](https://falcosecurity.github.io/kernel-crawler/x86_64/list.json)

A weekly [github action workflow](https://github.com/falcosecurity/kernel-crawler/actions/workflows/update-kernels.yml) will open a PR on this repo to update the json.  
As soon as the PR is merged and the json updated, a [prow job](https://github.com/falcosecurity/test-infra/blob/master/config/jobs/update-dbg/update-dbg.yaml) will create a PR on [test-infra](https://github.com/falcosecurity/test-infra) to generate the new Driverkit configs from the updated json.

## Usage

Helper text and options:

Main:
```commandline
Usage: kernel-crawler [OPTIONS] COMMAND [ARGS]...

Options:
    --debug / --no-debug
    --help                Show this message and exit.

Commands:
    crawl
```

Crawl command:
```commandline
Usage: kernel-crawler crawl [OPTIONS]

Options:
    --distro [alinux|almalinux|amazonlinux2|amazonlinux2022|amazonlinux2023|arch|bottlerocket|centos|debian|fedora|flatcar|minikube|ol|opensuse|photon|redhat|rocky|talos|ubuntu|*]
    --version TEXT
    --arch [x86_64|aarch64]
    --image TEXT                    Option is required when distro is Redhat.
    --help                          Show this message and exit.
```

## CI Usage

To better suit the CI usage, a [Github composite action](https://docs.github.com/en/actions/creating-actions/creating-a-composite-action) has been developed.  
Therefore, running kernel-crawler in your Github workflow is as easy as adding this step:
```
- name: Crawl kernels
  uses: falcosecurity/kernel-crawler@main
  with:
    # Desired architecture. Either x86_64 or aarch64.
    # Default: 'x86_64'.
    arch: 'aarch64'
    
    # Desired distro.
    # Refer to crawl command helper message (above) to check supported distros.
    # Default: '*'.
    distro: 'ubuntu'
```

> __NOTE:__ Since we don't use annotated tags, one cannot use eg: falcosecurity/kernel-crawler@v0, but only either exact tag name, branch name or commit hash.

## Docker image

A docker image is provided for releases, by a GitHub Actions workflow: `falcosecurity/kernel-crawler:latest`.
You can also build it yourself, by issuing:
```commandline
docker build -t falcosecurity/kernel_crawler -f docker/Dockerfile .
```
from project root.

## Install

To install the project, a simple `pip3 install .` from project root is enough.  

## Examples

* Crawl amazonlinux2 kernels:
```commandline
kernel-crawler crawl --distro=AmazonLinux2
```

* Crawl all supported distros kernels:
```commandline
kernel-crawler crawl --distro=*
```
| :exclamation: **Note**: Passing ```--image``` argument is supported with ```--distro=*``` |
|-------------------------------------------------------------------------------------------|

* Crawl Redhat kernels (specific to the container supplied), with no-formatted output:
```commandline
kernel-crawler crawl --distro=Redhat --image=redhat/ubi8:registered
```
