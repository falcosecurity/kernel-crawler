Home of the crawled kernels for the supported distros.

Supported architectures:
* [x86_64](x86_64/list.json)
* [aarch64](aarch64/list.json)

[Last run distro](./last_run_distro.txt) file is needed to let test-infra automation know which distro it should build configs for.  
It is automatically filled up by update-kernels ci (main branch) with either:  
* "*" to notify that configs for all distros need to be rebuilt
* distro name to notify that only a single distro update is needed
