# network.py
import socket
import threading
import itertools
from protocol import pack_message, read_message


class PeerConnection:
    _id_iter = itertools.count()

    def __init__(self, sock: socket.socket, addr):
        self.id = next(PeerConnection._id_iter)
        self.sock = sock
        self.addr = addr
        self.alive = True

    def close(self):
        self.alive = False
        try: self.sock.shutdown(socket.SHUT_RDWR)
        except: pass
        try: self.sock.close()
        except: pass


class PeerNode:
    """Quản lý P2P connection"""
    def __init__(self, ui_on_message, ui_on_status):
        self.ui_on_message = ui_on_message
        self.ui_on_status = ui_on_status

        self.server_sock = None
        self.connections = {}
        self.lock = threading.Lock()
        self.running = False

    def start_listening(self, host, port):
        if self.running: return

        self.running = True
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((host, port))
        self.server_sock.listen(5)

        self.ui_on_status(f"Listening on {host}:{port}")

        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server_sock.accept()
            except OSError:
                break

            peer = PeerConnection(conn, addr)

            with self.lock:
                self.connections[peer.id] = peer

            self.ui_on_status(f"Accepted connection from {addr}")
            threading.Thread(target=self._handle_peer, args=(peer,), daemon=True).start()

    def connect_to(self, host, port, timeout=5):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        try:
            sock.connect((host, port))
            peer = PeerConnection(sock, (host, port))

            with self.lock:
                self.connections[peer.id] = peer

            self.ui_on_status(f"Connected to {host}:{port}")
            threading.Thread(target=self._handle_peer, args=(peer,), daemon=True).start()

        except Exception as e:
            self.ui_on_status(f"Connection failed: {e}")
            sock.close()

    def _handle_peer(self, peer: PeerConnection):
        peer.sock.settimeout(1.0)  # FIX: không block và không disconnect lung tung

        try:
            while peer.alive and self.running:
                try:
                    msg = read_message(peer.sock)
                    self.ui_on_message(msg, peer)
                except socket.timeout:
                    continue
                except Exception as e:
                    self.ui_on_status(f"[Warning] Peer {peer.id}: {e}")
                    continue
        finally:
            with self.lock:
                self.connections.pop(peer.id, None)

            peer.close()
            self.ui_on_status(f"Peer {peer.id} disconnected")

    def send_text(self, text, target_id=None):
        msg_obj = {"type": "msg", "text": text}
        data = pack_message(msg_obj)

        with self.lock:
            targets = (
                self.connections.values()
                if target_id is None
                else [self.connections.get(target_id)]
            )

        for peer in targets:
            if not peer:
                continue
            try:
                peer.sock.sendall(data)
            except Exception as e:
                self.ui_on_status(f"Send error -> Peer {peer.id}: {e}")

    def list_peers(self):
        with self.lock:
            return list(self.connections.values())

    def disconnect_peer(self, peer_id: int):
        with self.lock:
            peer = self.connections.pop(peer_id, None)
        if peer:
            peer.close()
            self.ui_on_status(f"Disconnected peer {peer_id}")

    def close(self):
        self.running = False
        if self.server_sock:
            self.server_sock.close()

        with self.lock:
            peers = list(self.connections.values())
            self.connections.clear()

        for p in peers:
            p.close()

        self.ui_on_status("Node closed")
