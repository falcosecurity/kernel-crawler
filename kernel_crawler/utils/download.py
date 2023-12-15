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

    # if 404, silently fail
    if resp.status_code == 404:
        return None
    else:  # if any other error, raise the error - might be a bug in crawler
        resp.raise_for_status()

    # if no error, return the contents
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
    for idx, url in enumerate(urls):
        try:
            content = get_url(url)
            # If content is None and we got elements after this one,
            # try the next ones.
            if content is not None or idx == len(urls) - 1:
                return content
        except Exception as exc:
            last_exc = exc
    raise last_exc
