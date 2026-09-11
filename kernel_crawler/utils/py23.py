def make_bytes(s):
    try:
        return s.encode('utf-8')
    except AttributeError:
        return s


def make_string(s, errors='strict'):
    try:
        return s.decode('utf-8', errors=errors)
    except AttributeError:
        return s
