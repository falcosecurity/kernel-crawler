FROM python:3.8-slim-buster

WORKDIR /app

COPY . .
RUN pip3 install .

COPY ./docker/root /

ENTRYPOINT [ "entrypoint" ]
