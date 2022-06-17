import socket
import hashlib
import os
from pathlib import Path


CHUNK_SIZE = 2**16


temp_file = "temp.file"
to_delete_file = "todelete.file"


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


def single_file_to_home_file(single_file):
    return Path(str(Path(single_file).parts[-1]) + ".home")


def on_request(sock: socket, req, to_send: str, to_send_is_bytes=False):
    request = sock.recv(1024).decode("ASCII")
    if request == req:
        if to_send_is_bytes:
            sock.sendall(to_send)
            return True
        sock.sendall(to_send.encode("ASCII"))
        return True
    return False


class Manager:
    def __init__(self, comm, search_dir=None, single_file=None):
        self.comm = comm
        self.search_dir = Path(search_dir)
        self.local_files = []
        if search_dir is None and single_file is None:
            raise Exception("Lacking search_dir or single_file (Both are == None)")

        if single_file is not None:
            self.do_single_file(single_file)
            return

        self.get_local_files()

    def do_single_file(self, single_file):
        locfile = LocalFile(single_file, "", 0)
        single_file_home = single_file_to_home_file(single_file)
        with open(single_file_home, "r") as f:
            locfile.ver = int(f.readline().rstrip("\n"))

        # mnbmnbmnb

    def get_local_files(self):
        pass


class Communicator:
    def __init__(self, port=59595, host="127.0.0.1"):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

    def get_files_within_home(self, home):
        self.sock.sendall(f"REQ_FILES_IN_HOME:{home}".encode("ASCII"))
        chunk_recved = self.sock.recv(2**28).decode("ASCII")
        out = []
        for n in chunk_recved.split("\n"):
            ns = n.split("///")
            out.append(netfile_from_net_path(ns[0], int(ns[1])))
        return out

    def get_file_ver(self, netfile):
        self.sock.sendall(f"REQ_FILE_VER:{netfile.net_path}".encode("ASCII"))
        return int(self.sock.recv(1024))

    def add_or_update_file(self, locfile: LocalFile):
        netfile = loc_to_netfile(locfile)

        num_of_chunks = os.path.getsize(locfile.local_path) // CHUNK_SIZE + 1

        self.sock.sendall(b"REQ_ADD_FILE")
        on_request(self.sock, "REQ_HOME", str(netfile.home))
        on_request(self.sock, "REQ_PATH", str(netfile.path))
        on_request(self.sock, "REQ_VER", str(netfile.ver))
        on_request(self.sock, "REQ_CHUNK_SIZE", str(CHUNK_SIZE))
        on_request(self.sock, "REQ_NUM_OF_CHUNKS", str(num_of_chunks))

        made_hash = send_file(self.sock, locfile.local_path, CHUNK_SIZE, num_of_chunks)
        on_request(self.sock, "REQ_HASH", made_hash, to_send_is_bytes=True)


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


def netfile_from_net_path(net_path, ver):
    p = Path(net_path)
    if len(p.parts) > 1:
        return NetFile(p.parent, Path(p.parts[0]), ver)
    return NetFile(Path(net_path), Path(""), ver)


def net_to_locfile(netfile):
    return LocalFile(netfile.path, file_manager.net_home_to_loc_home(netfile.home), netfile.ver)


def loc_to_netfile(locfile):
    return NetFile(locfile.path, locfile.path_home.parts[-1], locfile.ver)


def send_file(sock, filepath, chunk_size, num_of_chunks):
    hasher = hashlib.sha256()
    with open(filepath, "br") as f:
        for n in range(num_of_chunks):
            print("r")
            request = sock.recv(1024)
            print("rd")
            if b"REQ_CHUNK_" not in request:
                sock.sendall(b"FAIL")
                return False
            chunk_num = int(request[len(b"REQ_CHUNK_"):])
            if not chunk_num == n:
                sock.sendall(b"FAIL")
                return False

            read = f.read(chunk_size)
            hasher.update(read)
            sock.sendall(read)

    return hasher.digest()


class ServerPath:
    def __init__(self, string):
        self.path = string

    def __repr__(self):
        return self.path


if __name__ == "__main__":
    c = Communicator()
    file_manager.add_dir("clientdir")
    print(c.get_file(NetFile("not_temp_file.file", "clientdir", 0)))
    print(c.get_file(NetFile("more_not_file.file", "clientdir", 0)))
