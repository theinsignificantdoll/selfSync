import socket


class Manager:
    def __init__(self):
        pass


class Communicator:
    def __init__(self, port=59595, host="192.168.3.41"):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

    def get_file(self, NetFile):
        self.sock.sendall(b"")

    def recv_file(self):
        pass

    def activate_file(self):
        pass


class LocalFile:
    def __init__(self):
        pass


class NetFile:
    def __init__(self):
        pass
