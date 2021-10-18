# Running an on-prem probe builder

The probe builder can be used to automatically build kernel modules for the [commercial Sysdig agent](https://sysdig.com/). It can run on any host with Docker installed, including (with some preparation) air-gapped hosts.

The description below assumes that we need to build probes for:
* agent 12.0.0 (substitute the version as required)
* for RedHat/CentOS kernels
  * for Ubuntu kernels use -k CustomUbuntu option instead of -k CustomCentOS
  * for Debian kernels use -k CustomDebian option instead of -k CustomCentOS

## Prerequisites

### Downloading kernel packages

To prebuild probes for a particular kernel, you need the headers package for that particular kernel, along
with its dependencies.

For RedHat-like OSes (RHEL, CentOS, Fedora, etc.), the required packages are usually:
* `kernel-<VERSION>.rpm`
* `kernel-devel-<VERSION>.rpm`
* `kernel-core-<VERSION>.rpm` (if present)

For Debian-like OSes (Debian, Ubuntu, etc.), the required packages are usually:
* `linux-image-<VERSION>.deb`
* `linux-headers-<VERSION>.deb`

But please note that the set of required packages varies across distributions and versions, so providing
an exhaustive list is not possible here.

You can use the `kernel-crawler.py` script to determine the set of packages for a particular kernel.
To use it, pass a distribution name (one of the following) and, optionally, the specific kernel version
or its subset.

The output is a list of URLs directly to the kernel packages. For example, to download all the packages
needed to build the CentOS 4.18.0-305.10.2.el8\_4 kernel, you can run:

    # .../path/to/kernel-crawler.py CentOS 4.18.0-305.10.2.el8_4 | xargs wget -c
    (...)
    # ls -la
    total 61556
    drwxr-xr-x 2 root root     4096 Aug 12 15:55 .
    drwxr-xr-x 9 root root     4096 Aug 12 15:53 ..
    -rw-r--r-- 1 root root  6169556 Jul 20 21:12 kernel-4.18.0-305.10.2.el8_4.x86_64.rpm
    -rw-r--r-- 1 root root 37552272 Jul 20 21:12 kernel-core-4.18.0-305.10.2.el8_4.x86_64.rpm
    -rw-r--r-- 1 root root 19290066 Aug 12 15:55 kernel-devel-4.18.0-305.10.2.el8_4.x86_64.rpm

Then you can pass the directory containing the kernel files to the probe builder container
(`/directory-containing-kernel-packages/` in the examples below).

Distributions supported by the kernel crawler:
 - AmazonLinux
 - AmazonLinux2
 - CentOS
 - CoreOS
 - Debian
 - Fedora
 - Ubuntu

Please note that you do *not* need to extract or install the kernel packages on the build host.
The probe builder works on package files directly and extracts them internally.

## With internet access

```
git clone https://github.com/draios/probe-builder
git clone https://github.com/draios/agent-libs

docker build -t sysdig-probe-builder probe-builder/

cd agent-libs
git checkout agent/12.0.0
cd ..

docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /a-directory-with-some-free-space/:/workspace \
  -v $(pwd)/agent-libs:/sysdig \
  -v /directory-containing-kernel-packages/:/kernels \
  sysdig-probe-builder:latest -B -- \
  -p sysdigcloud-probe -v 12.0.0 -k CustomCentOS
```

## Air-gapped setup

### **(internet access required)** Prepare the builder images

**Note:** this takes a long time but is a one-time task

```
git clone https://github.com/draios/probe-builder
docker build -t airgap/sysdig-probe-builder probe-builder/

docker run --rm -v /var/run/docker.sock:/var/run/docker.sock airgap/sysdig-probe-builder:latest -P -b airgap/
docker save airgap/sysdig-probe-builder | gzip > builders.tar.gz
```

If you are going to build probes for Ubuntu kernels, you will also need an `ubuntu:latest`
image on your airgapped host. You can ship it using a very similar approach:

```
docker pull ubuntu
docker save ubuntu | gzip > ubuntu.tar.gz
```

### **(internet access required)** Download the kernel packages

This is left as an exercise for the reader. Note that the packages should not be unpacked or installed.

### **(internet access required)** Get the right sysdig source

```
git clone https://github.com/draios/agent-libs
cd agent-libs
git archive agent/12.0.0 --prefix sysdig/ | gzip > sysdig.tar.gz
```

### Ship builders.tar.gz, sysdig.tar.gz and the kernels to the air-gapped host
Again, exercise for the reader

### **(air-gapped host)** Load the builder images (again, slow and one-time)

```
zcat builders.tar.gz | docker load
```

### **(air-gapped host)** Unpack the sysdig source

```
tar xzf sysdig.tar.gz
```

it will create sysdig/ in the current directory

### **(air-gapped host)** Run the probe builder

**Note:** This is a single long command

```
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /a-directory-with-some-free-space/:/workspace \
  -v /wherever-you-unpacked/sysdig/:/sysdig \
  -v /directory-containing-kernel-packages/:/kernels \
  airgap/sysdig-probe-builder:latest -B -b airgap/ -- \
  -p sysdigcloud-probe -v 12.0.0 -k CustomCentOS
```

The probes will appear in `/a-directory-with-some-free-space/output`. That directory can be served over HTTP and the URL to the server used as `SYSDIG_PROBE_URL` when loading the module (e.g. agent-kmodule container).
