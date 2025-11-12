# protocol.py
import json
import struct

HEADER = struct.Struct('!I')  # 4 bytes unsigned int (message length)

def pack_message(obj: dict) -> bytes:
    """Đóng gói dict thành message dạng length-prefix"""
    data = json.dumps(obj).encode('utf-8')
    return HEADER.pack(len(data)) + data


def recv_exact(sock, n: int) -> bytes:
    """Đọc đúng n bytes (TCP có thể trả về từng phần)"""
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Peer disconnected")
        buf += chunk
    return buf


def read_message(sock) -> dict:
    """Đọc message gồm 4-byte header + payload JSON"""
    (length,) = HEADER.unpack(recv_exact(sock, HEADER.size))
    payload = recv_exact(sock, length)
    return json.loads(payload.decode('utf-8'))
