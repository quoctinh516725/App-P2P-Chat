# app.py
import tkinter as tk
from tkinter import ttk
from network import PeerNode


class P2PApp:
    def __init__(self, root):
        self.root = root
        self.root.title("P2P Chat - No Server (multi-peer)")

        self.node = PeerNode(self.on_message, self.on_status)

        # UI Layout
        frm = ttk.Frame(root)
        frm.pack(padx=10, pady=10)

        ttk.Label(frm, text="Peer IP").grid(row=0, column=0)
        ttk.Label(frm, text="Port").grid(row=0, column=2)

        self.ip_entry = ttk.Entry(frm, width=12)
        self.port_entry = ttk.Entry(frm, width=6)

        self.ip_entry.insert(0, "127.0.0.1")
        self.port_entry.insert(0, "5555")

        self.ip_entry.grid(row=0, column=1)
        self.port_entry.grid(row=0, column=3)

        ttk.Button(frm, text="Start Listening", command=self.start_listening).grid(row=0, column=4)
        ttk.Button(frm, text="Connect", command=self.connect).grid(row=0, column=5)

        # ================== Peer List ==================
        self.peer_list = tk.Listbox(root, width=40, height=6)
        self.peer_list.pack()

        ttk.Button(root, text="Refresh", command=self.refresh_peers).pack()
        ttk.Button(root, text="Disconnect", command=self.disconnect_selected).pack()

        # ================== Chat Box ==================
        self.chatbox = tk.Text(root, height=15)
        self.chatbox.pack()

        self.message_entry = ttk.Entry(root, width=50)
        self.message_entry.pack(side="left")

        ttk.Button(root, text="Send -> All", command=self.send_all).pack(side="right")

    def start_listening(self):
        ip = self.ip_entry.get()
        port = int(self.port_entry.get())
        self.node.start_listening(ip, port)

    def connect(self):
        ip = self.ip_entry.get()
        port = int(self.port_entry.get())
        self.node.connect_to(ip, port)

    def refresh_peers(self):
        self.peer_list.delete(0, tk.END)
        for p in self.node.list_peers():
            self.peer_list.insert(tk.END, f"{p.id} -> {p.addr}")

    def disconnect_selected(self):
        selected = self.peer_list.curselection()
        if selected:
            peer_id = int(self.peer_list.get(selected).split(" ")[0])
            self.node.disconnect_peer(peer_id)

    def send_all(self):
        msg = self.message_entry.get()
        if msg:
            self.node.send_text(msg)
            self.chatbox.insert(tk.END, f"Me -> ALL: {msg}\n")
            self.message_entry.delete(0, tk.END)

    def on_message(self, msg, peer):
        self.chatbox.insert(tk.END, f"[Peer {peer.id}] {msg['text']}\n")

    def on_status(self, text):
        self.chatbox.insert(tk.END, f"[Status] {text}\n")


root = tk.Tk()
app = P2PApp(root)
root.mainloop()
