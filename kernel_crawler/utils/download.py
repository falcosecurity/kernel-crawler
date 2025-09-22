import bz2
import zlib
import zstandard
import requests
import io

try:
    import lzma
except ImportError:
    from backports import lzma

from requests.exceptions import (
    ConnectTimeout,
    ReadTimeout,
    Timeout,
    ConnectionError,
    RequestException,
)


def get_url(url):
    try:
        resp = requests.get(
            url,
            headers={  # some URLs require a user-agent, otherwise they return HTTP 406 - this one is fabricated
                'user-agent': 'dummy'
            },
            timeout=15,
        )

        # if 404, silently fail
        if resp.status_code == 404:
            return None
        else:  # if any other error, raise the error - might be a bug in crawler
            resp.raise_for_status()

        # if no error, return the (eventually decompressed) contents
        if url.endswith('.gz'):
            return zlib.decompress(resp.content, 47)
        elif url.endswith('.xz'):
            return lzma.decompress(resp.content)
        elif url.endswith('.bz2'):
            return bz2.decompress(resp.content)
        elif url.endswith('.zst'):
            with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(resp.content)) as rr:
                return rr.read()
        else:
            return resp.content

    except (ConnectTimeout, ReadTimeout, Timeout):
        print(f"[ERROR] Timeout fetching {url}")
    except ConnectionError:
        print(f"[ERROR] Network unreachable or host down: {url}")
    except RequestException as e:
        print(f"[ERROR] Request failed for {url}: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected error fetching {url}: {e}")
    return None


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
