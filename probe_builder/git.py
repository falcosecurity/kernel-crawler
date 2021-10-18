import os

from probe_builder import spawn


def clone(repo_url, branch, target_dir):
    if not os.path.exists(target_dir):
        spawn.pipe(['git', 'clone', repo_url, target_dir])
    spawn.pipe(['git', 'checkout', branch], silence_errors=False, cwd=target_dir)
