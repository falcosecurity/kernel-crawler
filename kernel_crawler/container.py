import docker

class Container():
    def __init__(self, image):
        self.image = image

    def run_cmd(self, cmd, encoding ="utf-8"):
        client = docker.from_env()
        container = client.containers.run(self.image, cmd, detach=True)
        logs = container.attach(stdout=True, stderr=True, stream=True, logs=True)
        cmd_output = []
        for line in logs:
            decoded_line = line.decode(encoding)
            sp = list(filter(None, decoded_line.split("\n")))
            cmd_output.extend(sp)
        return cmd_output