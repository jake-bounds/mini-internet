import socket


class Host:
    def __init__(self, host_port: int):
        self.host_port = host_port
        self.sock: socket.socket = None

    def __enter__(self):
        self.sock = socket.socket()
