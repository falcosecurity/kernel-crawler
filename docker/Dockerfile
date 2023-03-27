FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends git=1:2.30.* && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
COPY setup.py .
COPY kernel_crawler ./kernel_crawler

RUN pip3 install --no-cache-dir . && \
    useradd --create-home appuser

USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH

ENTRYPOINT ["kernel-crawler"]
