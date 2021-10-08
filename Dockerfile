FROM alpine

RUN apk add \
    bash \
    gawk \
    grep \
	curl \
    dpkg \
	rpm2cpio \
	git \
	jq \
	multipath-tools \
	python3 \
	py3-lxml \
	wget \
    docker

RUN ln -s /usr/bin/python3 /usr/bin/python

ADD . /builder
WORKDIR /builder
ENTRYPOINT [ "/builder/main-builder-entrypoint.sh" ]
