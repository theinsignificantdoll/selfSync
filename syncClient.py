import socket
import hashlib
import os


temp_file = "temp.file"
to_delete_file = "todelete.file"


class Manager:
    def __init__(self):
        pass


class Communicator:
    def __init__(self, port=59595, host="127.0.0.1"):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

    def get_file(self, netfile):
        """
        gets file from server

        :param netfile:
        :return True if success, otherwise False:
        """
        recved_file_hash = self.recv_file(netfile)
        if recved_file_hash is False:
            return False
        if not self.check_file_integrity(recved_file_hash):
            return False
        self.activate_file(netfile)

    def recv_file(self, netfile):
        """
        download netfile as temp.file

        :param netfile:
        :return: True if success otherwise False
        """

        self.sock.sendall(f"recv_file:{netfile.path}".encode("ASCII"))
        print("recving")
        response = self.sock.recv(1024)
        print("recved")
        if not response == b"Affirmative":
            return False
        try:
            self.sock.sendall(b"REQ_NUM_OF_CHUNKS")
            print("r")
            response = self.sock.recv(1024)
            print("rd")
            num_of_chunks = int(response)

            self.sock.sendall(b"REQ_CHUNK_SIZE")
            print("r")
            response = self.sock.recv(1024)
            print("rd")
            chunk_size = int(response)
        except TypeError:
            return False

        hasher = hashlib.sha256()
        with open(temp_file, "bw+") as f:
            print(num_of_chunks)
            for n in range(num_of_chunks):
                self.sock.sendall(f"REQ_CHUNK_{n}".encode("ASCII"))
                print("rr")
                response = self.sock.recv(chunk_size+1024)
                print("rrdd")
                if response == b"FAIL":
                    print(response)
                    return False

                f.write(response)
                hasher.update(response)
        temp_file_hash = hasher.digest()
        return temp_file_hash

    def check_file_integrity(self, temp_file_hash=None):
        """
        checks temp.file integrity (hash)

        :param temp_file_hash: If None: calculate hash manually; otherwise: use given.
        :param netfile:
        :return: True if Success otherwise False
        """

        if temp_file_hash is None:
            hasher = hashlib.sha256()

        self.sock.sendall(b"REQ_NET_HASH")
        server_hash = self.sock.recv(1024)
        if temp_file_hash == server_hash:
            return True
        print(server_hash)
        print("Non-matching hash")
        return False

    def activate_file(self, netfile):
        """
        activates temp.file. I.e. moves it, and registers it

        :return: True if success otherwise False
        """
        locfile = net_to_locfile(netfile)
        if os.path.exists(locfile.path):
            os.rename(locfile.path, to_delete_file)
        os.rename(temp_file, locfile.path)
        os.remove(to_delete_file)
        return True


def net_to_locfile(netfile):
    return LocalFile(netfile.path)


class ServerPath:
    def __init__(self, string):
        self.path = string

    def __repr__(self):
        return self.path


class LocalFile:
    def __init__(self, path):
        self.path = path


class NetFile:
    def __init__(self, path):
        self.path = path


if __name__ == "__main__":
    c = Communicator()
    print(c.get_file(NetFile("not_temp_file.file")))
    print(c.get_file(NetFile("more_not_file.file")))
