# Running an on-prem probe builder

The probe builder can be used to automatically build kernel modules for [OSS Sysdig](https://github.com/draios/sysdig) as well as the [commercial Sysdig agent](https://sysdig.com/). It can run on any host with Docker installed, including (with some preparation) air-gapped hosts.

The description below assumes that we need to build probes for agent 12.0.0 (substitute the version as required) for RHEL/CentOS kernels. Whenever kernel packages are mentioned, it means kernel-VERSION.rpm and kernel-devel-VERSION.rpm files (with matching VERSION). A similar process can be used for Ubuntu kernels (linux-image-VERSION.deb, linux-headers-VERSION.deb and possibly others) with the -k CustomUbuntu option in place of -k CustomCentOS.

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
