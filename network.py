import socket
import threading
from queue import Queue
from protocol import pack_message, read_message

class PeerNode:
    def __init__(self, ui_on_message, ui_on_status):
        self.server = None
        self.conn = None
        self.running = False
        self.msg_queue = Queue()
        self.ui_on_message = ui_on_message
        self.ui_on_status(f"Connected to {ip}:{port}")
        self.running = True
        threading.Thread(target=self._recv_loop, daemon=True).start()

    def _recv_loop(self):
        try:
            while self.running:
                msg = read_message(self.conn)
                self.msg_queue.put(msg)
                self.ui_on_message(msg)
        except Exception as e:
            self.ui_on_status(f"Connection closed: {e}")
            self.running = False

    def send_text(self, text):
        if not self.conn:
            raise RuntimeError("Not connected")
        self.conn.sendall(pack_message({"type": "msg", "text": text}))

    def close(self):
        self.running = False
        try:
            if self.conn: self.conn.close()
            if self.server: self.server.close()
        except:
            pass

