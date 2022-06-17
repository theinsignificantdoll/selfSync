import socket
import time
import os
import hashlib
from pathlib import Path


serverstor = Path("serverstor")
if not serverstor.exists():
    with open(serverstor, "w+") as f:
        pass


def localfile_from_local_path(local_path, ver):
    p = Path(local_path)
    if len(p.parts) > 1:
        return LocalFile(p.parent, Path(p.parts[0]), ver)
    return LocalFile(Path(local_path), Path(""), ver)


class LocalFile:
    def __init__(self, path, home, ver):
        self.path = Path(path)
        self.home = Path(home)
        self.ver = ver
        self.local_path = home / path


class FileManager:
    def __init__(self, serverstor=serverstor):
        self.serverstor = serverstor
        self.stored_files = {}   # KEY should be equal to LocalFile.local_path

    def read_stor(self):
        with open(self.serverstor, "r") as f:
            while True:
                r = f.readline().rstrip("\n")
                if r == "":
                    break
                p = r.split("///")
                local_path = p[0]
                ver = int(p[1])
                l = localfile_from_local_path(local_path, ver)

                self.stored_files[l.local_path] = l

    def write_stor(self):
        with open(self.serverstor, "w+") as f:
            for d in self.stored_files:
                f.write(f"{d}///{self.stored_files[d].ver}\n")


class RequestHandler:
    def __init__(self, sock, chunk_size=2**16):
        self.sock = sock
        self.chunk_size = chunk_size

    def loop(self):
        request = self.sock.recv(1024)
        if request.split(b":")[0] == b"recv_file":
            print(self.file_request_handler(request.decode("ASCII").split(":")[1]))
        elif request.split(b":")[0] == b"REQ_FILES_IN_HOME":
            print(self.files_in_home_handler(Path(str(request.split(b":")[1]))))

    def files_in_home_handler(self, home):
        pass

    def file_request_handler(self, netfile):
        print(netfile)
        filepath = netfile
        full_file_path = serverstor / filepath
        file_size = os.path.getsize(full_file_path)
        num_of_chunks = file_size // self.chunk_size + 1
        self.sock.sendall(b"Affirmative")
        request = self.sock.recv(1024)
        if request == b"REQ_NUM_OF_CHUNKS":
            self.sock.sendall(str(num_of_chunks).encode("ASCII"))

        request = self.sock.recv(1024)
        if request == b"REQ_CHUNK_SIZE":
            self.sock.sendall(str(self.chunk_size).encode("ASCII"))

        local_file_hash = send_file(self.sock, full_file_path, self.chunk_size, num_of_chunks)
        if local_file_hash is False:
            return False
        return send_hash(self.sock, local_file_hash)


def send_hash(sock, local_file_hash):
    request = sock.recv(1024)
    print("requesting hash?")
    if not request == b"REQ_NET_HASH":
        return False
    print("sending hash")

    sock.sendall(local_file_hash)
    return True


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


if __name__ == "__main__":
    globsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    globsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    globsock.bind(("0.0.0.0", 59595))
    globsock.listen(1)
    handle, address = globsock.accept()
    print(address)
    h = RequestHandler(handle)
    while True:
        h.loop()
        time.sleep(0.1)
