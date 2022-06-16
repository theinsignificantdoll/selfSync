import socket
import hashlib
import os
from pathlib import Path


temp_file = "temp.file"
to_delete_file = "todelete.file"


class FileManager:
    def __init__(self):
        self.net_homes = {}  # USES Path OBJECTS
        self.within_net_home = []

    def net_home_to_loc_home(self, net_home):
        try:
            return self.net_homes[net_home]
        except KeyError:
            return ""

    def add_dir(self, path):
        p = Path(path)
        self.net_homes[p.parts[-1]] = p

    def update_within_net_home(self, home, comm):
        pass


file_manager = FileManager()


class Manager:
    def __init__(self, comm, search_dir=None, single_file=None):
        self.comm = comm
        if search_dir is None and single_file is None:
            raise Exception("Lacking search_dir or single_file (Both are == None)")
        if single_file is not None:
            self.do_single_file(single_file)

            return
        self.search_dir = search_dir

    def do_single_file(self, single_file):
        pass


class Communicator:
    def __init__(self, port=59595, host="127.0.0.1"):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

    def get_files_within_home(self, home):
        self.sock.sendall(f"REQ_FILES_IN_HOME:{home}".encode("ASCII"))

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
        self.sock.sendall(f"recv_file:{netfile.net_path}".encode("ASCII"))
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
        if os.path.exists(locfile.local_path):
            os.rename(locfile.local_path, to_delete_file)
        os.rename(temp_file, locfile.local_path)
        if os.path.exists(to_delete_file):
            os.remove(to_delete_file)
        return True


def net_to_locfile(netfile):
    return LocalFile(netfile.path, file_manager.net_home_to_loc_home(netfile.home), netfile.ver)


def loc_to_netfile(locfile):
    return NetFile(locfile.path, locfile.home.parts[-1], locfile.ver)


class ServerPath:
    def __init__(self, string):
        self.path = string

    def __repr__(self):
        return self.path


class LocalFile:
    def __init__(self, path, home, ver):
        self.path = Path(path)
        self.path_home = Path(home)
        self.ver = ver
        self.local_path = self.path_home / self.path


class NetFile:
    def __init__(self, path, home, ver):
        self.path = Path(path)
        self.home = Path(home)
        self.ver = ver
        self.net_path = self.home / self.path


if __name__ == "__main__":
    c = Communicator()
    file_manager.add_dir("clientdir")
    print(c.get_file(NetFile("not_temp_file.file", "clientdir", 0)))
    print(c.get_file(NetFile("more_not_file.file", "clientdir", 0)))
