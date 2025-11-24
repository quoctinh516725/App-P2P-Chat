#network.py
import socket
import threading
import traceback
from queue import Queue
from protocol import pack_message, read_message, b64_encode, b64_decode
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Random import get_random_bytes
import json, os

def json_bytes(obj: dict) -> bytes:
    return json.dumps(obj, separators=(',',':')).encode('utf-8')

def json_loads(b: bytes) -> dict:
    return json.loads(b.decode('utf-8'))

class ConnectionHandler:
    def __init__(self, sock: socket.socket, addr, owner, is_server_side: bool):
        self.sock = sock
        self.addr = addr
        self.owner = owner
        self.running = True
        self.aes_key = None
        self.is_server_side = is_server_side
        self.lock = threading.Lock()
        threading.Thread(target=self._recv_loop, daemon=True).start()

    def send_plain(self, obj: dict):
        with self.lock:
            self.sock.sendall(pack_message(obj))

    def send_encrypted(self, obj: dict):
        if self.aes_key is None:
            raise RuntimeError("No AES key")
        plain = json_bytes(obj)
        cipher = AES.new(self.aes_key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(plain)
        payload = cipher.nonce + tag + ciphertext
        enc = b64_encode(payload)
        self.send_plain({"type":"enc","data":enc})

    def close(self):
        self.running = False
        try: self.sock.close()
        except: pass

    def _perform_server_handshake(self, client_pub_pem: str):
        client_pub = RSA.import_key(client_pub_pem.encode('utf-8'))
        aes_key = get_random_bytes(32)
        rsa_cipher = PKCS1_OAEP.new(client_pub)
        encrypted = rsa_cipher.encrypt(aes_key)
        self.send_plain({"type":"aes_key","data":b64_encode(encrypted)})
        self.aes_key = aes_key

    def _perform_client_handshake(self):
        msg = read_message(self.sock)
        if msg.get("type") != "aes_key":
            raise RuntimeError("Expected aes_key from server")
        encrypted = b64_decode(msg["data"])
        rsa_cipher = PKCS1_OAEP.new(self.owner.rsa_key)
        self.aes_key = rsa_cipher.decrypt(encrypted)

    def _recv_loop(self):
        try:
            if getattr(self, "is_server_side", False):
                msg = read_message(self.sock)
                if msg.get("type") != "pubkey":
                    raise RuntimeError("Expected pubkey")
                client_pem = msg.get("pem")
                self.send_plain({"type":"pubkey","pem":self.owner.public_pem})
                self._perform_server_handshake(client_pem)
                self.owner._on_handshake_complete(self)
            else:
                self.send_plain({"type":"pubkey","pem":self.owner.public_pem})
                self._perform_client_handshake()
                self.owner._on_handshake_complete(self)

            while self.running:
                msg = read_message(self.sock)
                if not isinstance(msg, dict): continue
                typ = msg.get("type")
                if typ == "enc":
                    payload = b64_decode(msg.get("data"))
                    nonce = payload[:16]; tag = payload[16:32]; ciphertext = payload[32:]
                    cipher = AES.new(self.aes_key, AES.MODE_GCM, nonce=nonce)
                    plain = cipher.decrypt_and_verify(ciphertext, tag)
                    inner = json_loads(plain)
                    self.owner._handle_decrypted(self, inner)
                else:
                    self.owner._handle_control(self, msg)
        except ConnectionError as e:
            self.owner._on_connection_error(self, e)
        except Exception as e:
            traceback.print_exc()
            self.owner._on_connection_error(self, e)
        finally:
            self.close()
            self.owner._on_connection_closed(self)

class PeerNode:
    def __init__(self, ui_on_message, ui_on_status):
        self.server_sock = None
        self.running = False
        self.handlers = {}
        self.ui_on_message = ui_on_message
        self.ui_on_status = ui_on_status
        self.lock = threading.Lock()
        self.rsa_key = RSA.generate(2048)
        self.public_pem = self.rsa_key.publickey().export_key().decode('utf-8')
        self.username = None
        self.password = None

    def set_login_info(self, username, password):
        self.username = username
        self.password = password

    def start_listening(self, host='0.0.0.0', port=5555):
        if not self.username: raise RuntimeError("Login required")
        if self.server_sock: raise RuntimeError("Already listening")
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((host, port))
        self.server_sock.listen(5)
        self.running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        self.ui_on_status(f"Listening on {host}:{port}")

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server_sock.accept()
                handler = ConnectionHandler(conn, addr, owner=self, is_server_side=True)
                with self.lock:
                    self.handlers[addr] = handler
                self.ui_on_status(f"Incoming connection from {addr}")
            except Exception as e:
                self.ui_on_status(f"Accept error: {e}")
                break

    def connect_to(self, ip, port):
        if not self.username: raise RuntimeError("Login required")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        addr = sock.getpeername()
        handler = ConnectionHandler(sock, addr, owner=self, is_server_side=False)
        with self.lock:
            self.handlers[addr] = handler
        self.ui_on_status(f"Connected to {addr}")

    def _on_handshake_complete(self, handler):
        self.ui_on_status(f"Handshake complete with {handler.addr}")

    def _handle_decrypted(self, handler, msg):
        self.ui_on_message({"peer": handler.addr, **msg})

    def _handle_control(self, handler, msg):
        typ = msg.get("type")
        if typ == "pubkey":
            self.ui_on_status(f"Received pubkey from {handler.addr}")
        else:
            self.ui_on_status(f"Control msg from {handler.addr}: {msg}")

    def _on_connection_error(self, handler, exc):
        self.ui_on_status(f"Connection {handler.addr} error: {exc}")

    def _on_connection_closed(self, handler):
        addr = handler.addr
        with self.lock:
            if addr in self.handlers: del self.handlers[addr]
        self.ui_on_status(f"Connection closed: {addr}")

    def send_text_to(self, addr, text, nick=None):
        with self.lock: handler = self.handlers.get(addr)
        if not handler: raise RuntimeError("No such connection")
        payload = {"type":"msg","text":text}
        if nick: payload["from"] = nick
        handler.send_encrypted(payload)

    def broadcast_text(self, text, nick=None):
        with self.lock: conns = list(self.handlers.values())
        for h in conns:
            try:
                payload = {"type":"msg","text":text}
                if nick: payload["from"] = nick
                h.send_encrypted(payload)
            except Exception as e:
                self.ui_on_status(f"Send to {h.addr} failed: {e}")

    # file send
    def send_file_to(self, addr, filepath, chunk_size=64*1024):
        if not os.path.isfile(filepath): raise RuntimeError("File not found")
        fname = os.path.basename(filepath)
        total = os.path.getsize(filepath)
        with open(filepath,'rb') as f:
            with self.lock: handler = self.handlers.get(addr)
            if not handler: raise RuntimeError("No such connection")
            handler.send_encrypted({"type":"file_start","filename":fname,"size":total})
            while True:
                chunk = f.read(chunk_size)
                if not chunk: break
                handler.send_encrypted({"type":"file_chunk","data":b64_encode(chunk)})
            handler.send_encrypted({"type":"file_end","filename":fname})
        self.ui_on_status(f"File {fname} sent to {addr}")

    def broadcast_file(self, filepath):
        with self.lock: addrs = list(self.handlers.keys())
        for addr in addrs:
            try:
                self.send_file_to(addr, filepath)
            except Exception as e:
                self.ui_on_status(f"File send to {addr} failed: {e}")

    def list_peers(self):
        with self.lock: return list(self.handlers.keys())

    def close(self):
        self.running = False
        with self.lock: hs = list(self.handlers.values())
        for h in hs: h.close()
        if self.server_sock:
            try: self.server_sock.close()
            except: pass
