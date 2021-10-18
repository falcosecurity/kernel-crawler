def make_bytes(s):
    try:
        return s.encode('utf-8')
    except AttributeError:
        return s


def make_string(s):
    try:
        return s.decode('utf-8')
    except AttributeError:
        return s
