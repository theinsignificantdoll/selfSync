import socket
import time
import os
import hashlib
from pathlib import Path


temp_file = Path("temp_server.file")
to_delete_file = Path("todelete.file")


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

    def files_in_home(self, home):
        out = []
        for d in self.stored_files:
            if self.stored_files[d].home == home:
                out.append(self.stored_files[d])
        return out

    def add_or_update_local_file(self, locfile: LocalFile):
        self.stored_files[locfile.local_path] = locfile

    def get_ver(self, net_path):
        return self.stored_files[Path(net_path)].ver


def make_request(sock: socket, req: str):
    sock.sendall(req.encode("ASCII"))
    response = sock.recv(1024).decode("ASCII")
    return response


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
        elif request.split(b":")[0] == b"REQ_FILE_VER":
            print(self.file_ver_handler(Path(str(request.split(b":")[1]))))
        elif request.split(b":")[0] == b"REQ_ADD_FILE":
            print(self.file_add_handler())

    def file_add_handler(self):
        home = make_request(self.sock, "REQ_HOME")
        path = make_request(self.sock, "REQ_PATH")
        ver = int(make_request(self.sock, "REQ_VER"))
        chunk_size = int(make_request(self.sock, "REQ_CHUNK_SIZE"))
        num_of_chunks = int(make_request(self.sock, "REQ_NUM_OF_CHUNKS"))
        locfile = LocalFile(path, home, ver)
        made_hash = self.recv_file(locfile, chunk_size, num_of_chunks)
        if made_hash is False:
            return False

        recved_hash = make_request(self.sock, "REQ_HASH")
        if recved_hash != made_hash:
            return False

        return self.activatefile(locfile)

    def recv_file(self, locfile, chunk_size, num_of_chunks):
        hasher = hashlib.sha256()
        with open(temp_file, "bw+") as f:
            for n in range(num_of_chunks):
                self.sock.sendall(f"REQ_CHUNK_{n}".encode("ASCII"))
                chunk = self.sock.recv(chunk_size+1024)
                if chunk == b"FAIL":
                    return False

                hasher.update(chunk)
                f.write(chunk)
        return hasher.digest()

    def activatefile(self, locfile):
        if locfile.local_path.exists():
            os.rename(locfile.local_path, to_delete_file)
        os.rename(temp_file, locfile.local_path)
        file_manager.add_or_update_local_file(locfile)
        os.remove(to_delete_file)
        return True

    def file_ver_handler(self, netpath):
        local_file_ver = file_manager.get_ver(netpath)
        self.sock.sendall(f"{local_file_ver}".encode("ASCII"))

    def files_in_home_handler(self, home):
        files_in_home = file_manager.files_in_home(home)
        chunk_to_send = ""
        for n in files_in_home:
            chunk_to_send += f"{n.local_path}///{n.ver}\n"
        self.sock.sendall(chunk_to_send.encode("ASCII"))

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
    file_manager = FileManager()
    file_manager.read_stor()

    globsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    globsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    globsock.bind(("0.0.0.0", 59595))
    globsock.listen(1)
    handle, address = globsock.accept()

    h = RequestHandler(handle)
    while True:
        h.loop()
        time.sleep(0.1)

