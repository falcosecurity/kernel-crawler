# Developer notes

## Data flow through the application

Based on the command line arguments, a distribution is chosen.
This amounts to:
* a `DistroBuilder` subclass, containing distro-specific code
* a distribution name, used mostly as a directory name to store downloaded kernels
* a builder distro name, used to select a set of Dockerfiles to choose from
* a crawler distro name, passed to the kernel crawler (which has its own set of supported distributions)

Wherever `DistroBuilder` is mentioned in this document, it means a *subclass*
of the `DistroBuilder` class.

### Building probes from local files

#### Batching packages

The input is a list of paths to local files. `DistroBuilder.batch_packages` is called
to group the packages into kernel versions, resulting in a dictionary of arrays:

```json
{
  "5.4.0-1": [
    "kernel-5.4.0-1.x86_64.rpm",
    "kernel-devel-5.4.0-1.x86_64.rpm"
  ],
  "5.5.0-10": [
    "kernel-5.5.0-10.x86_64.rpm",
    "kernel-devel-5.5.0-10.x86_64.rpm"
  ]
}
```

(the package names here are obviously fake).

**Note:** this process doesn't inspect the packages themselves and only
relies on file names (like the old probe builder did). This means it may
be less accurate or completely wrong in some situations.

#### Unpacking the packages

The dictionary created above is passed to `DistroBuilder.unpack_kernels`.
This method uses distro-specific (or rather packager-specific) code to unpack
all packages in the per-release directories.

It returns a map of release->directory, similar to:

```json
{
  "5.4.0-1": ".../build/debian/5.4.0-1",
  "5.5.0-10": ".../build/debian/5.5.0-10"
}
```

(the directories are named in a way that is compatible with the old builder
so the mapping isn't always trivial, e.g. for Ubuntu kernels whose versioning
is somewhat complicated).

#### Building the kernels

For each (release, directory) pair returned from `unpack_kernels`,
`DistroBuilder.build_kernels` is called. This method is common to all
builders but it has per-distro extension points:

  * `get_kernel_dir`: return the full path to the kernel headers
    (the directory passed in is the root of the filesystem where the packages are extracted to,
    and the actual kernel directory is a subdirectory like `<directory>/usr/src/linux-headers-5.4.0-1`)
  * `hash_config`: return the MD5 hash of the kernel's config file
    (the config file is stored in different places for different distributions
    and this method knows where)

The rest of the code is distro-agnostic.

### Building probes for all kernels in a distribution

The kernel crawler has its own set of supported distributions, mostly
overlapping with the `DistroBuilder`s but e.g. Amazon Linux, Fedora and Oracle
Linux are compatible enough that they can use the CentOS builder, even though
they need their own crawlers (even if only to specify the list of mirrors).

In the crawler, each distribution is a set of mirrors, each of which can contain one
or more repositories. A repository knows how to parse its metadata and return a map
of release->list of URLs:

```json
{
  "5.4.0-1": [
    "http://.../kernel-5.4.0-1.x86_64.rpm",
    "http://.../kernel-devel-5.4.0-1.x86_64.rpm"
  ],
  "5.5.0-10": [
    "http://.../kernel-5.5.0-10.x86_64.rpm",
    "http://.../kernel-devel-5.5.0-10.x86_64.rpm"
  ]
}
```

The result of the crawler is used in `DistroBuilder.crawl` to download all
packages and replace the URLs with file paths. This is identical to the result
of `DistroBuilder.batch_packages` (used with local files), except that
the crawler understands repository metadata (which we don't have with local files)
so should generally make a better job of getting the right packages together.

The steps to unpack and build the kernels are identical in both cases.