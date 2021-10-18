from functools import total_ordering


@total_ordering
class Version(object):
    major = None
    minor = None

    def __init__(self, version_str):
        major, minor = version_str.split('.')[:2]
        self.major = int(major)
        self.minor = int(minor)

    def __eq__(self, other):
        return (self.major, self.minor) == (other.major, other.minor)

    def __lt__(self, other):
        return (self.major, self.minor) < (other.major, other.minor)

    def __str__(self):
        return '{}.{}'.format(self.major, self.minor)

    def __repr__(self):
        return str(self)



