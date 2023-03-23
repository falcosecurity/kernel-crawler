import bz2
import zlib
import requests
try:
    import lzma
except ImportError:
    from backports import lzma

def get_url(url):
    resp = requests.get(
        url,
        headers={  # some URLs require a user-agent, otherwise they return HTTP 406 - this one is fabricated
            'user-agent': 'dummy'
        }
    )
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
