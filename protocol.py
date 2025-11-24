import json
import struct

HEADER = struct.Struct('!I')  # 4 byte big-endian

def pack_message(obj: dict) -> bytes:
    data = json.dumps(obj).encode('utf-8')
    return HEADER.pack(len(data)) + data

def recv_exact(sock, n: int) -> bytes:
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Peer closed")
        buf += chunk
    return buf

def read_message(sock) -> dict:
    (length,) = HEADER.unpack(recv_exact(sock, HEADER.size))
    payload = recv_exact(sock, length)
    return json.loads(payload.decode('utf-8'))
