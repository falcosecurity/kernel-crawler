FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
COPY setup.py .
COPY kernel_crawler ./kernel_crawler

RUN pip3 install --no-cache-dir . && \
    useradd --create-home appuser

USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH

ENTRYPOINT ["kernel-crawler"]
