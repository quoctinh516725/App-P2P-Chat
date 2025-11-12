import socket
import ssl
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from protocol import pack_message, read_message   # <-- dùng file protocol.py

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5555

CERT_FILE = "client.crt"
KEY_FILE = "client.key"
CA_CERT = "ca.crt"


class ChatClientGUI:
    def __init__(self, master):
        self.master = master
        master.title("Secure Chat Client (SSL)")

        self.text_area = scrolledtext.ScrolledText(master, state="disabled", width=50, height=20)
        self.text_area.pack(pady=10)

        self.entry = tk.Entry(master, width=40)
        self.entry.pack(side=tk.LEFT, padx=5, pady=5)

        self.send_btn = tk.Button(master, text="Send", command=self.send_message)
        self.send_btn.pack(side=tk.LEFT)

        self.sock = None
        self.ssl_sock = None

        self.connect()

    def connect(self):
        """Tạo socket và kết nối đến server bằng SSL"""
        try:
            raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
            context.load_verify_locations(CA_CERT)
            context.verify_mode = ssl.CERT_REQUIRED

            self.ssl_sock = context.wrap_socket(raw_sock, server_hostname="MyChatServer")
            self.ssl_sock.connect((SERVER_HOST, SERVER_PORT))

            threading.Thread(target=self.receive_loop, daemon=True).start()

            self.show_message("✅ Connected to server\n")

        except Exception as e:
            messagebox.showerror("Connection failed", str(e))
            exit(1)

    def send_message(self):
        text = self.entry.get()
        if not text:
            return

        obj = {"type": "chat", "message": text}
        self.ssl_sock.sendall(pack_message(obj))
        self.entry.delete(0, tk.END)

    def receive_loop(self):
        """Nhận liên tục từ server"""
        try:
            while True:
                msg = read_message(self.ssl_sock)
                self.show_message(f"[Server]: {msg['message']}\n")
        except Exception:
            self.show_message("❌ Disconnected from server\n")

    def show_message(self, msg):
        self.text_area.configure(state="normal")
        self.text_area.insert(tk.END, msg)
        self.text_area.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    gui = ChatClientGUI(root)
    root.mainloop()
