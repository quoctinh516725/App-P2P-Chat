import socket
import threading
import itertools
from queue import Queue
from protocol import pack_message, read_message

class PeerConnection:
    
    _id_iter = itertools.count()
    def __init__(self, sock: socket.socket, addr):
        self.id = next(PeerConnection._id_iter)
        self.sock = sock 
        self.addr = addr
        self.alive = True
    
    def fileno(self):
        return self.sock.fileno()
    def close(self):
        self.alive = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except:
            pass
        try:
            self.sock.close()
        except:
            pass
class PeerNode:
    def __init__(self, ui_on_message, ui_on_status):
        self.server = None
        self.connections = {}
        self.lock = threading.Lock()
        self.running = False
        self.ui_on_message = ui_on_message
        self.ui_on_status = ui_on_status


    def start_listening(self, host='0.0.0.0', port=5555):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(1)
        self.running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        self.ui_on_status(f"Listening on {host}:{port}...")

    def _accept_loop(self):
        try:
            self.conn, addr = self.server.accept()
            self.ui_on_status(f"Connected with {addr}")
            threading.Thread(target=self._recv_loop, daemon=True).start()
        except Exception as e:
            self.ui_on_status(f"Accept error: {e}")

    def connect_to(self, ip, port):
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((ip, port))
        self.ui_on_status(f"Connected to {ip}:{port}")
        self.running = True
        threading.Thread(target=self._recv_loop, daemon=True).start()
    def start_listening(self, ip, port):
        if self.server_sock:
            raise RuntimeError("Already listening")
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((ip, port))
        self.server_sock.listen(5)
        self.server_sock.setblocking(False)
        self.ui_on_status(f"Listening on {ip}:{port}")
        threading.Thread(target=self._accept_loop, daemon=True).start()
    def _accept_loop(self):
        try:
            while self.running:
                try:
                    conn, addr = self.server_sock.accept()
                    with self.lock:
                        peer = PeerConnection(conn, addr)
                        self.connections[peer.id] = peer
                    self.ui_on_status(f"Accepted connection from {addr}")
                    threading.Thread(target=self._handle_peer, args=(peer,), daemon=True).start()
                except BlockingIOError:
                    continue
        except Exception as e:
            self.ui_on_status(f"Accept loop error: {e}")
            self.running = False
    def connect_to(self, ip, port, timeout=5):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((ip, port))
            peer = PeerConnection(sock, (ip, port))
            with self.lock:
                self.connections[peer.id] = peer
            self.ui_on_status(f"Connected to {ip}:{port}")
            threading.Thread(target=self._handle_peer, args=(peer,), daemon=True).start()
        except Exception as e:
            self.ui_on_status(f"Connection to {ip}:{port} failed: {e}")
            sock.close()    
    def _recv_loop(self, conn: PeerConnection):
        try:
            while self.running and conn.alive:
                try:
                    msg = read_message(conn.sock)
                except ConnectionError as ce:
                    self.ui_on_status(f"Peer {conn.id} disconnected: {ce}")
                    break
                except Exception as e:
                    self.ui_on_status(f"Read error from {conn.id}: {e}")
                    break

                # gửi lên UI kèm connection info
                try:
                    self.ui_on_message(msg, conn)
                except Exception:
                    # đảm bảo không crash thread nếu UI có vấn đề
                    pass
        finally:
            # cleanup this connection
            with self.lock:
                if conn.id in self.connections:
                    del self.connections[conn.id]
            try:
                conn.close()
            except:
                pass
            self.ui_on_status(f"Connection {conn.id} closed")

    def send_text(self, text: str, target_id: int = None):
        """
        Nếu target_id là None -> gửi cho tất cả peer đang kết nối.
        Nếu target_id được cung cấp -> gửi cho peer đó (nếu tồn tại).
        """
        msg_obj = {"type": "msg", "text": text}
        data = pack_message(msg_obj)
        sent_to = []
        with self.lock:
            if target_id is None:
                conns = list(self.connections.values())
            else:
                conn = self.connections.get(target_id)
                if not conn:
                    raise RuntimeError(f"Peer {target_id} not connected")
                conns = [conn]

        for conn in conns:
            try:
                conn.sock.sendall(data)
                sent_to.append(conn.id)
            except Exception as e:
                self.ui_on_status(f"Send error to {conn.id}: {e}")
        return sent_to

    def list_peers(self):
        with self.lock:
            return list(self.connections.values())

    def disconnect_peer(self, peer_id: int):
        with self.lock:
            conn = self.connections.pop(peer_id, None)
        if conn:
            conn.close()
            self.ui_on_status(f"Disconnected peer {peer_id}")
        else:
            raise RuntimeError(f"Peer {peer_id} not found")

    def close(self):
        self.running = False
        # close server socket first to unblock accept
        try:
            if self.server_sock:
                self.server_sock.close()
        except:
            pass

        # close all connections
        with self.lock:
            conns = list(self.connections.values())
            self.connections.clear()
        for c in conns:
            try:
                c.close()
            except:
                pass
        self.ui_on_status("Node closed")
