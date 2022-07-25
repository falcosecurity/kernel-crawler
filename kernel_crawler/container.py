import docker
import click

def decoded_str(s):
    if s is None:
        return ''
    return s.partition(b'\n')[0].decode("utf-8")

class Container():
    def __init__(self, image):
        self.image = image

    def run_cmd(self, cmd, encoding ="utf-8"):
        client = docker.from_env()
        container = client.containers.run(self.image, cmd, detach=True)
        logs = container.attach(stdout=True, stderr=True, stream=True, logs=True)
        # Depending on the command, the output could be buffered so first amalgamate
        # into one byte stream so that the outut can be processed correctly.
        with click.progressbar(logs, label='[' + self.image + '] Running command \'' + cmd + '\'', item_show_func=decoded_str) as logs:
            output = b''
            for line in logs:
                output += line
        decoded_line = output.decode(encoding)
        cmd_output = list(filter(None, decoded_line.split("\n")))
        return cmd_output
