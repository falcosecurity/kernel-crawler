import json
import logging
import subprocess

from probe_builder.py23 import make_bytes, make_string

logger = logging.getLogger(__name__)


def pipe(cmd, silence_errors=False, cwd=None):
    cmd = [make_bytes(c) for c in cmd]
    cmd_string = make_string(b' '.join(cmd))
    if cwd is not None:
        logger.info('Running {} in {}'.format(cmd_string, make_string(cwd)))
    else:
        logger.info('Running {}'.format(cmd_string))
    child = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdout, _) = child.communicate(None)
    if not silence_errors and child.returncode != 0:
        logger.warn('{} returned error code {}'.format(cmd_string, child.returncode))
        for line in stdout.splitlines(False):
            logger.warn(make_string(line))
        raise subprocess.CalledProcessError(child.returncode, cmd_string)
    else:
        lines = stdout.splitlines(False)
        for line in lines:
            logger.debug(make_string(line))
        return lines


def json_pipe(cmd, silence_errors=False, cwd=None):
    cmd = [make_bytes(c) for c in cmd]
    cmd_string = make_string(b' '.join(cmd))
    if cwd is not None:
        logger.info('Running {} in {}'.format(cmd_string, make_string(cwd)))
    else:
        logger.info('Running {}'.format(cmd_string))
    child = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdout, _) = child.communicate(None)
    if not silence_errors and child.returncode != 0:
        logger.warn('{} returned error code {}'.format(cmd_string, child.returncode))
        for line in stdout.splitlines(False):
            logger.warn(line)
        raise subprocess.CalledProcessError(child.returncode, cmd_string)
    else:
        return json.loads(make_string(stdout))
