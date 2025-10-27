import tkinter as tk
from tkinter import scrolledtext, messagebox
from network import PeerNode

class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("P2P Chat - No Server")
        self.node = PeerNode(self.on_message, self.on_status)

        top = tk.Frame(root); top.pack(padx=8, pady=8, fill='x')
        tk.Label(top, text="Peer IP:").pack(side='left')
        self.ip_var = tk.StringVar(value="127.0.0.1")
        tk.Entry(top, textvariable=self.ip_var, width=15).pack(side='left', padx=4)
        tk.Label(top, text="Port:").pack(side='left')
        self.port_var = tk.IntVar(value=5555)
        tk.Entry(top, textvariable=self.port_var, width=6).pack(side='left', padx=4)

        tk.Button(top, text="Start Listening", command=self.start_listen).pack(side='left', padx=6)
        tk.Button(top, text="Connect", command=self.connect_peer).pack(side='left', padx=6)

        self.chat = scrolledtext.ScrolledText(root, state='disabled', wrap='word', height=18)
        self.chat.pack(padx=8, pady=8, fill='both', expand=True)

        bottom = tk.Frame(root); bottom.pack(padx=8, pady=8, fill='x')
        self.entry = tk.Entry(bottom)
        self.entry.pack(side='left', fill='x', expand=True)
        self.entry.bind("<Return>", self.send_msg)
        tk.Button(bottom, text="Send", command=self.send_msg).pack(side='left', padx=6)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def start_listen(self):
        try:
            self.node.start_listening(port=self.port_var.get())
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def connect_peer(self):
        try:
            self.node.connect_to(self.ip_var.get(), self.port_var.get())
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def send_msg(self, event=None):
        text = self.entry.get().strip()
        if not text: return
        try:
            self.node.send_text(text)
            self.append_chat(f"Me: {text}")
            self.entry.delete(0, 'end')
        except Exception as e:
            messagebox.showwarning("Warning", str(e))

    def on_message(self, msg: dict):
        if msg.get("type") == "msg":
            self.append_chat(f"Peer: {msg.get('text','')}")
        else:
            self.append_chat(f"[{msg}]")

    def on_status(self, text):
        self.append_chat(f"[Status] {text}")

    def append_chat(self, line):
        self.chat.configure(state='normal')
        self.chat.insert('end', line + "\n")
        self.chat.configure(state='disabled')
        self.chat.yview('end')

    def on_close(self):
        self.node.close()
        self.root.destroy()

