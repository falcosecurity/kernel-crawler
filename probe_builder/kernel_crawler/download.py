import bz2
import zlib
import requests
import shutil
from threading import Thread
import os

from probe_builder.context import DownloadConfig

try:
    import lzma
except ImportError:
    from backports import lzma

try:
    from queue import Queue
except ImportError:
    from Queue import Queue


def download_file(url, output_file, download_config=None):
    if download_config is None:
        download_config = DownloadConfig.default()
    resp = None
    for i in range(download_config.retries):
        with open(output_file, 'ab') as fp:
            size = fp.tell()
            if size > 0:
                headers = {'Range': 'bytes={}-'.format(size)}
            else:
                headers = {}
            if download_config.extra_headers is not None:
                headers.update(download_config.extra_headers)
            resp = requests.get(url, headers=headers, stream=True, timeout=download_config.timeout)
            if resp.status_code == 206:
                # yay, resuming the download
                shutil.copyfileobj(resp.raw, fp)
                return
            elif resp.status_code == 416:
                return  # "requested range not satisfiable", we have the whole thing
            elif resp.status_code == 200:
                fp.truncate(0)  # have to start over
                shutil.copyfileobj(resp.raw, fp)
                return

    resp.raise_for_status()
    raise requests.HTTPError('Unexpected status code {}'.format(resp.status_code))


def download_batch(urls, output_dir, download_config=None):
    if download_config is None:
        download_config = DownloadConfig.default()
    q = Queue(1)

    def dl():
        while True:
            url = q.get()
            output_file = os.path.join(output_dir, os.path.basename(url))
            download_file(url, output_file, download_config)
            q.task_done()

    for i in range(download_config.concurrency):
        t = Thread(target=dl)
        t.daemon = True
        t.start()

    for batch_url in urls:
        q.put(batch_url)

    q.join()


def get_url(url):
    resp = requests.get(url)
    resp.raise_for_status()
    if url.endswith('.gz'):
        return zlib.decompress(resp.content, 47)
    elif url.endswith('.xz'):
        return lzma.decompress(resp.content)
    elif url.endswith('.bz2'):
        return bz2.decompress(resp.content)
    else:
        return resp.content


def get_first_of(urls):
    last_exc = Exception('Empty url list')
    for url in urls:
        try:
            return get_url(url)
        except Exception as exc:
            last_exc = exc
    raise last_exc


if __name__ == '__main__':
    import sys

    _url = sys.argv[1]
    try:
        _output_file = sys.argv[2]
    except IndexError:
        _output_file = os.path.basename(_url)

    download_file(_url, _output_file)
