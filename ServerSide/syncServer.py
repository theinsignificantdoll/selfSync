#!/bin/python3
import socket
import time
import os
import hashlib
from pathlib import Path
import threading


host = "0.0.0.0"
port = 3434


soclist = []

has_exited = False


temp_file = Path("temp_server.f")
to_delete_file = Path("todeleteserver.f")
index_file = Path("index.f")
if not os.path.exists(index_file):
    with open(index_file, "w+") as f:
        pass


serverstor = Path("serverstor")
if not serverstor.exists():
    os.mkdir(serverstor)


def localfile_from_local_path(local_path, ver):
    p = Path(local_path)
    if len(p.parts) > 1:
        return LocalFile(get_path_from_full(p), Path(p.parts[0]), ver)
    return LocalFile(Path(local_path), Path(""), ver)


def get_path_from_full(full_path):
    parts = Path(full_path).parts
    if len(parts) == 1:
        return full_path
    return Path("/".join(parts[1:]))


class LocalFile:
    def __init__(self, path, home, ver):
        self.path = Path(path)
        self.home = Path(home)
        self.ver = ver
        self.local_path = self.home / self.path


class FileManager:
    def __init__(self, serverstor=serverstor):
        self.serverstor = serverstor
        self.stored_files = {}   # KEY should be equal to LocalFile.local_path

    def __str__(self):
        out = ""
        for n in self.stored_files:
            out += f"{n.local_path} {n.ver}\n"

    def read_stor(self):
        with open(index_file, "r") as f:
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
        with open(index_file, "w+") as f:
            for d in self.stored_files:
                f.write(f"{d}///{self.stored_files[d].ver}\n")

    def files_in_home(self, home):
        out = []
        for d in self.stored_files:
            if self.stored_files[d].home == home:
                out.append(self.stored_files[d])
        return out

    def add_or_update_local_file(self, locfile: LocalFile, append_to_index=True):
        self.stored_files[locfile.local_path] = locfile
        if append_to_index:
            self.append_to_index(locfile)

    def append_to_index(self, locfile: LocalFile):
        with open(index_file, "a") as f:
            f.write(f"{locfile.local_path}///{locfile.ver}\n")

    def get_ver(self, net_path):
        return self.stored_files[Path(net_path)].ver


def make_request(sock: socket, req: str):
    sock.sendall(req.encode("ASCII"))
    response = sock.recv(1024)
    return response


class RequestHandler:
    def __init__(self, sock, chunk_size=2**16):
        self.sock = sock
        self.chunk_size = chunk_size

    def loop(self):
        request = self.sock.recv(1024)
        if request == b"":
            return False
        if request.split(b":")[0] == b"recv_file":
            self.file_request_handler(request.decode("ASCII").split(":")[1])
        elif request.split(b":")[0] == b"REQ_FILES_IN_HOME":
            self.files_in_home_handler(Path(request.decode("ASCII").split(":")[1]))
        elif request.split(b":")[0] == b"REQ_FILE_VER":
            self.file_ver_handler(Path(str(request.split(b":")[1])))
        elif request.split(b":")[0] == b"REQ_ADD_FILE":
            self.file_add_handler(), "File_add_handler"
        elif request == b"REQ_SERVER_SAVE":
            file_manager.write_stor()
        return True

    def file_add_handler(self):
        home = make_request(self.sock, "REQ_HOME").decode("ASCII")
        path = make_request(self.sock, "REQ_PATH").decode("ASCII")
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
        if (serverstor / locfile.local_path).exists():
            os.rename(serverstor / locfile.local_path, to_delete_file)

        ensure_folder_exists(serverstor / locfile.local_path.parent)
        os.rename(temp_file, serverstor / locfile.local_path)
        file_manager.add_or_update_local_file(locfile)
        if to_delete_file.exists():
            os.remove(to_delete_file)
        return True

    def file_ver_handler(self, netpath):
        local_file_ver = file_manager.get_ver(netpath)
        self.sock.sendall(f"{local_file_ver}".encode("ASCII"))

    def files_in_home_handler(self, home):
        files_in_home = file_manager.files_in_home(home)
        chunk_to_send = ""
        if not files_in_home:
            self.sock.sendall(b"RESP_HOME_EMPTY")
            return
        for n in files_in_home:
            chunk_to_send += f"{n.local_path}///{n.ver}\n"
        self.sock.sendall(chunk_to_send.encode("ASCII"))

    def file_request_handler(self, netfile):
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


def ensure_folder_exists(path: Path):
    if path.exists() or path.parent == Path(""):
        return True
    ensure_folder_exists(path.parent)
    path.mkdir()
    return False


def send_hash(sock, local_file_hash):
    request = sock.recv(1024)
    if not request == b"REQ_NET_HASH":
        return False

    sock.sendall(local_file_hash)
    return True


def send_file(sock, filepath, chunk_size, num_of_chunks):
    hasher = hashlib.sha256()
    with open(filepath, "br") as f:
        for n in range(num_of_chunks):
            request = sock.recv(1024)
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


def loop_socklist():
    global soclist
    to_delete = []
    while not has_exited:
        for s in soclist:
            try:
                s_connected = s.loop()

                if not s_connected:
                    to_delete.append(s)

            except socket.timeout:
                continue
    for s in to_delete:
        soclist.remove(s)


if __name__ == "__main__":
    file_manager = FileManager()
    file_manager.read_stor()
    print("Loaded Index")

    globsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    globsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    globsock.bind((host, port))
    globsock.listen(1)
    print("Listening")
    loop_thread = threading.Thread(None, loop_socklist)
    loop_thread.start()

    while not has_exited:
        handle, address = globsock.accept()
        print(address, "Connected")
        handle.settimeout(0.01)

        h = RequestHandler(handle)
        soclist.append(h)
        time.sleep(0.1)

