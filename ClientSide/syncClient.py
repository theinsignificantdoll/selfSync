import socket
import hashlib
import os
from pathlib import Path


CHUNK_SIZE = 2**16


host = "127.0.0.1"
port = 3434


temp_file = Path("temp.f")
index_temp_file = Path("temp_index.f")
index_to_delete_file = Path("delete_index.f")
to_delete_file = Path("todelete.f")
index_extension = ".index"


def read_req(sock):
    req = b""
    while len(req) == 0 or req[-1] != 10:
        print("recvmomg`")
        req += sock.recv(1024)
        print(req)
    print(req)
    return req.rstrip(b"\n")


def _pass(_):
    pass


def home_to_home_index(home: str):
    return f"{Path(home).parts[-1]}{index_extension}"


def home_index_to_home(home_index: str):
    return home_index.rstrip(index_extension)


def get_all_files_in(path: Path):
    out = []
    for n in path.iterdir():
        if n.is_dir():
            out += [*get_all_files_in(n)]
        out.append(Path(n))
    return out


class LocalFile:
    def __init__(self, path, home, ver, timestamp=None):
        self.path = Path(path)
        self.home = Path(home)
        self.ver = ver
        self.local_path = self.home / self.path

        if timestamp is None:
            if not os.path.exists(self.local_path):
                self.timestamp = 0
            else:
                self.timestamp = int(os.path.getmtime(self.local_path))
        else:
            self.timestamp = timestamp

    def __repr__(self):
        return f"LocalFile({self.path}, {self.home}, {self.ver})"


class NetFile:
    def __init__(self, path, home, ver):
        self.path = Path(path)
        self.home = Path(home)
        self.ver = ver
        self.net_path = self.home / self.path

    def __repr__(self):
        return f"NetFile({self.path}, {self.home}, {self.ver})"


class FileManager:
    def __init__(self):
        self.net_homes = {}  # USES Path OBJECTS
        self.within_net_home = []
        self.local_files_within_home_index = {}  # {Path(Local_Path): LocalFile}
        self.local_files_not_in_home_index = []

    def net_home_to_loc_home(self, net_home):
        try:
            return self.net_homes[net_home.parts[-1]]
        except KeyError:
            raise Exception("HOME UNKNOWN")

    def add_dir(self, path):
        p = Path(path)
        self.net_homes[p.parts[-1]] = p

    def update_within_net_home(self, home, comm):
        self.within_net_home = comm.get_files_within_home(Path(home.parts[-1]))

    def update_local_files_within_home_index(self, home):
        self.local_files_within_home_index = self.read_home_index(home_to_home_index(home))

    def update_local_files_not_in_home_index(self, home):
        path_to_home = Path(self.net_home_to_loc_home(home))
        all_files = get_all_files_in(path_to_home)
        self.local_files_not_in_home_index = []
        for n in all_files:
            if str(n) not in self.local_files_within_home_index:
                self.local_files_not_in_home_index.append(LocalFile(n.relative_to(home.absolute()), home, 0))

    def read_home_index(self, home_index):
        out = {}
        if not Path(home_index).exists():
            with open(home_index, "w+") as f:
                return {}
        with open(home_index, "r") as f:
            while True:
                line = f.readline().rstrip("\n")
                if line == "":
                    break

                splitline = line.split("///")
                out[splitline[0]] = (local_file_from_local_path(splitline[0], int(splitline[1]), int(splitline[2])))
        return out

    def write_local_files_to_home_index(self, home):
        home_index = Path(home_to_home_index(str(home)))
        with open(index_temp_file, "w+") as f:
            for n in self.local_files_within_home_index:
                locfile = self.local_files_within_home_index[n]
                f.write(f"{locfile.local_path}///{locfile.ver}///{locfile.timestamp}\n")

        if home_index.exists():
            os.rename(home_index, index_to_delete_file)

        os.rename(index_temp_file, home_index)

        if index_to_delete_file.exists():
            os.remove(index_to_delete_file)

    def add_file_to_home_index(self, locfile):
        self.local_files_within_home_index[str(locfile.local_path)] = locfile

    def write_single_file(self, locfile):
        with open(single_file_to_home_file(locfile.local_path), "w+") as f:
            f.write(f"{locfile.local_path}\n")
            f.write(f"{locfile.ver}\n")
            f.write(f"{locfile.timestamp}\n")

    def get_single_file(self, single_file):
        if not Path(single_file_to_home_file(single_file)).exists():
            self.write_single_file(local_file_from_local_path(single_file, 0))
        with open(single_file_to_home_file(single_file)) as f:
            local_path = f.readline().rstrip("\n")
            ver = int(f.readline().rstrip("\n"))
            timestamp = int(f.readline().rstrip("\n"))
            return local_file_from_local_path(local_path, ver, timestamp)


file_manager = FileManager()


def single_file_to_home_file(single_file):
    return Path(str(Path(single_file).parts[-1]) + ".home")


def on_request(sock: socket, req, to_send: str, to_send_is_bytes=False):
    request = read_req(sock).decode("ASCII")

    if request == req:
        if to_send_is_bytes:
            sock.sendall(to_send + b"\n")
            return True
        sock.sendall((to_send + "\n").encode("ASCII"))
        return True
    return False


class Manager:
    def __init__(self, comm, search_dir=None, single_file=None):
        self.comm = comm
        self.local_files = []
        if search_dir is None and single_file is None:
            raise Exception("Lacking search_dir or single_file (Both are == None)")

        if single_file is not None:
            self.do_single_file(single_file)
            return
        self.search_dir = Path(search_dir)
        self.download_missing_files()
        self.download_outdated()
        self.upload_missing_files()
        file_manager.write_local_files_to_home_index(search_dir)

    def do_single_file(self, single_file):
        locfile = file_manager.get_single_file(single_file)
        netfile = self.comm.get_files_within_home(locfile.home.parts[-1])
        found_file = False
        for n in netfile:
            if n.path == locfile.path:
                found_file = True
                if n.ver > locfile.ver or not Path(single_file).exists():
                    self.comm.get_file(n, locfile.home)
                    locfile.ver = n.ver
                    locfile.timestamp = int(os.path.getmtime(locfile.local_path))
                    file_manager.write_single_file(locfile)
                continue
        if not found_file:
            self.comm.add_or_update_file(locfile)
            file_manager.write_single_file(locfile)
            return

        if locfile.timestamp < int(os.path.getmtime(single_file)):
            self.comm.add_or_update_file(locfile)
            locfile.timestamp = int(os.path.getmtime(single_file))
            file_manager.write_single_file(locfile)

    def download_missing_files(self):
        file_manager.update_within_net_home(self.search_dir, self.comm)
        file_manager.update_local_files_within_home_index(self.search_dir)
        file_manager.update_local_files_not_in_home_index(self.search_dir)
        for n in file_manager.within_net_home:
            locfile = net_to_locfile(n)
            if str(locfile.local_path) not in file_manager.local_files_within_home_index or not locfile.local_path.exists():
                self.comm.get_file(n)
                file_manager.add_file_to_home_index(locfile)

    def download_outdated(self):
        for n in file_manager.within_net_home:
            locfile = net_to_locfile(n)
            if n.ver > file_manager.local_files_within_home_index[str(locfile.local_path)].ver:
                self.comm.get_file(n)
                locfile.timestamp = int(os.path.getmtime(locfile.local_path))
                locfile = net_to_locfile(n)
                file_manager.add_file_to_home_index(locfile)

    def upload_missing_files(self):
        for n in file_manager.local_files_not_in_home_index:
            self.comm.add_or_update_file(n)
            file_manager.add_file_to_home_index(n)


class Communicator:
    def __init__(self, port=port, host=host, when_upload_callback=_pass, when_download_callback=_pass):
        self.host = host
        self.port = port
        self.when_upload_callback = when_upload_callback
        self.when_download_callback = when_download_callback
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

    def massive_chunk(self, chunk_size):
        req = b""
        print("massive chunk")
        while len(req) == 0 or req[-2:] != b"\n\n":
            req += self.sock.recv(chunk_size)
        print("massive chink out")
        return req.rstrip(b"\n")

    def get_files_within_home(self, home):
        self.sock.sendall(f"REQ_FILES_IN_HOME:{str(home)}\n".encode("ASCII"))
        chunk_recved = self.massive_chunk(2**28).decode("ASCII")

        if chunk_recved == "RESP_HOME_EMPTY":
            return []

        out = []
        for n in chunk_recved.split("\n"):
            if n == "":
                break
            ns = n.split("///")
            out.append(netfile_from_net_path(ns[0], int(ns[1])))
        return out

    def get_file_ver(self, netfile):
        self.sock.sendall(f"REQ_FILE_VER:{netfile.net_path}\n".encode("ASCII"))
        return int(read_req(self.sock))

    def add_or_update_file(self, locfile: LocalFile):
        netfile = loc_to_netfile(locfile)

        num_of_chunks = 0
        file_size = os.path.getsize(locfile.local_path)
        if file_size != 0:
            num_of_chunks = file_size // CHUNK_SIZE + 1

        self.sock.sendall(b"REQ_ADD_FILE\n")
        on_request(self.sock, "REQ_HOME", str(netfile.home.parts[-1]))
        on_request(self.sock, "REQ_PATH", str(netfile.path.as_posix()))
        on_request(self.sock, "REQ_VER", str(netfile.ver))
        on_request(self.sock, "REQ_CHUNK_SIZE", str(CHUNK_SIZE))
        on_request(self.sock, "REQ_NUM_OF_CHUNKS", str(num_of_chunks))

        made_hash = send_file(self.sock, locfile.local_path, CHUNK_SIZE, num_of_chunks)
        locfile.ver += 1
        on_request(self.sock, "REQ_HASH", made_hash, to_send_is_bytes=True)
        self.when_upload_callback(locfile.local_path)

    def get_file(self, netfile, optional_placement=None):
        """
        gets file from server

        :param netfile:
        :param optional_placement:
        :return True if success, otherwise False:
        """
        recved_file_hash = self.recv_file(netfile)
        if recved_file_hash is False:
            return False
        if not self.check_file_integrity(recved_file_hash):
            return False
        end_path = self.activate_file(netfile, optional_placement)

        self.when_download_callback(Path(end_path))

    def recv_file(self, netfile):
        """
        download netfile as temp.file

        :param netfile:
        :return: True if success otherwise False
        """
        self.sock.sendall(f"recv_file:{netfile.net_path}\n".encode("ASCII"))
        response = read_req(self.sock)
        if not response == b"Affirmative":
            return False
        try:
            self.sock.sendall(b"REQ_NUM_OF_CHUNKS\n")
            response = read_req(self.sock)
            num_of_chunks = int(response)

            self.sock.sendall(b"REQ_CHUNK_SIZE\n")
            response = read_req(self.sock)
            chunk_size = int(response)
        except TypeError:
            return False

        hasher = hashlib.sha256()
        with open(temp_file, "bw+") as f:
            for n in range(num_of_chunks):
                self.sock.sendall(f"REQ_CHUNK_{n}\n".encode("ASCII"))
                response = self.sock.recv(chunk_size+1024)
                if response == b"<<FAIL>>\n":
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

        self.sock.sendall(b"REQ_NET_HASH\n")
        server_hash = read_req(self.sock)
        if temp_file_hash == server_hash:
            return True
        return False

    def activate_file(self, netfile, optional_placement=None):
        """
        activates temp.file. I.e. moves it, and registers it

        :return: True if success otherwise False
        """
        locfile = net_to_locfile(netfile)
        end_path = locfile.local_path
        if optional_placement is not None:
            end_path = optional_placement / locfile.path

        if os.path.exists(end_path):
            os.rename(end_path, to_delete_file)

        if optional_placement is None:
            ensure_folder_exists(locfile.path, locfile.home)
        else:
            ensure_folder_exists(end_path, Path(optional_placement))

        os.rename(temp_file, end_path)

        if os.path.exists(to_delete_file):
            os.remove(to_delete_file)
        return end_path

    def trigger_server_index_save(self):
        self.sock.sendall(b"REQ_SERVER_SAVE\n")


def get_path_from_full(full_path):
    parts = Path(full_path).parts
    if len(parts) == 1:
        return full_path
    return Path("/".join(parts[1:]))


def netfile_from_net_path(net_path, ver):
    p = Path(net_path)
    if len(p.parts) > 1:
        return NetFile(get_path_from_full(p), Path(p.parts[0]), ver)
    return NetFile(Path(net_path), Path(""), ver)


def local_file_from_local_path(local_path, ver, timestamp=None):
    p = Path(local_path)
    if len(p.parts) > 1:
        return LocalFile(get_path_from_full(p), Path(p.parts[0]), ver, timestamp)
    return LocalFile(Path(local_path), Path(""), ver, timestamp)


def net_to_locfile(netfile):
    return LocalFile(netfile.path, file_manager.net_home_to_loc_home(netfile.home), netfile.ver)


def loc_to_netfile(locfile):
    if locfile.home == Path(""):
        return NetFile(locfile.path, "", locfile.ver)
    return NetFile(locfile.path, locfile.home.parts[-1], locfile.ver)


def ensure_folder_exists(path: Path, home: Path):
    if path.exists() or path.parent == Path("") or path.parent == Path(home):
        return True
    ensure_folder_exists(path.parent, home)
    path.mkdir()
    return False


def send_file(sock, filepath, chunk_size, num_of_chunks):
    hasher = hashlib.sha256()
    with open(filepath, "br") as f:
        for n in range(num_of_chunks):
            request = read_req(sock)
            if b"REQ_CHUNK_" not in request:
                sock.sendall(b"<<FAIL>>\n")
                return False
            chunk_num = int(request[len(b"REQ_CHUNK_"):])
            if not chunk_num == n:
                sock.sendall(b"<<FAIL>>\n")
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


def do_dir(direc, when_upload_callback=_pass, when_download_callback=_pass):
    c = Communicator(when_upload_callback=when_upload_callback, when_download_callback=when_download_callback)
    file_manager.add_dir(direc)
    Manager(c, direc)
    c.trigger_server_index_save()


def do_single_file(path, when_upload_callback=_pass, when_download_callback=_pass):
    c = Communicator(when_upload_callback=when_upload_callback, when_download_callback=when_download_callback)
    file_manager.add_dir(path)
    Manager(c, single_file=path)
    c.trigger_server_index_save()
