FROM python:3.10-slim

WORKDIR /app

COPY . .
RUN pip3 install .

COPY ./docker/root /

ENTRYPOINT [ "entrypoint" ]
