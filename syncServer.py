import socket
import time
import os
import hashlib


class RequestHandler:
    def __init__(self, sock, chunk_size=65536):
        self.sock = sock
        self.chunk_size = chunk_size

    def loop(self):
        request = self.sock.recv(1024)
        if request.split(b":")[0] == b"recv_file":
            self.file_request_handler(request.decode("ASCII").split(":")[1])

    def file_request_handler(self, netfile):
        filepath = netfile  # CHANGE ME LATER
        file_size = os.path.getsize(filepath)
        num_of_chunks = file_size // self.chunk_size + 1
        self.sock.sendall(b"Affirmative")
        request = self.sock.recv(1024)
        if request == b"REQ_NUM_OF_CHUNKS":
            self.sock.sendall(str(num_of_chunks).encode("ASCII"))

        request = self.sock.recv(1024)
        if request == b"REQ_CHUNK_SIZE":
            self.sock.sendall(str(self.chunk_size).encode("ASCII"))

        local_file_hash = send_file(self.sock, filepath, self.chunk_size, num_of_chunks)


def send_hash(sock, local_file_hash):
    request = sock.recv(1024)
    if not request == b"REQ_NET_HASH":
        return False

    sock.sendall(local_file_hash)


def send_file(sock, filepath, chunk_size, num_of_chunks):
    hasher = hashlib.sha256()
    with open(filepath, "r") as f:
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
            print(read)
            sock.sendall(read.encode("utf8"))

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

