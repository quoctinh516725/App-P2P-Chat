import tkinter as tk
from tkinter import scrolledtext, messagebox
from network import PeerNode

from tkinter import messagebox, scrolledtext
import socket   
from network import PeerNode     # Assuming network.py contains P2PNetwork class

class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("P2P Chat - No Server")
        self.node = PeerNode(self.on_message, self.on_status)


        self.root.title("P2P Chat-No Server (multi-peer)")
        def safe_on_message(msg):
            self.root.after(0, lambda: self.on_message(msg))
        def safe_on_status(status):
            self.root.after(0, lambda: self.on_status(status))
        self.node = PeerNode(safe_on_message, safe_on_status)
        

        top = tk.Frame(root); top.pack(padx=8, pady=8, fill='x')
        tk.Label(top, text="Peer IP:").pack(side='left')
        self.ip_var = tk.StringVar(value="127.0.0.1")
        tk.Entry(top, textvariable=self.ip_var, width=15).pack(side='left', padx=4)
        tk.Label(top, text="Port:").pack(side='left')
        self.port_var = tk.IntVar(value=5555)
        tk.Entry(top, textvariable=self.port_var, width=6).pack(side='left', padx=4)

        tk.Button(top, text="Start Listening", command=self.start_listen).pack(side='left', padx=6)
        tk.Button(top, text="Connect", command=self.connect_peer).pack(side='left', padx=6)

        
        middle = tk.Frame(root); middle.pack(padx=8, pady=4, fill='both', expand=True)
        #Peer list
        peer_frame = tk.Frame(middle)
        peer_frame.pack(side='left',padx=4,  fill='y')
        tk.Label(peer_frame, text="Connected Peers:").pack(anchor='w')
        self.peer_listbox = tk.Listbox(peer_frame, height=8, width=28)
        self.peer_listbox.pack(side='left', fill='y')
        peer_btn_frame = tk.Frame(peer_frame)
        peer_btn_frame.pack(side='left', padx=4, fill='y')
        tk.Button(peer_btn_frame, text="Refresh", command=self.refresh_peers).pack(fill='x')
        tk.Button(peer_btn_frame, text="Disconnect", command=self.disconnect_peer).pack(fill= 'x', pady=4)
        tk.Button(peer_btn_frame, text="Send -> Selected", command=lambda:self.send_to_selected).pack(fill='x')
        #Chat  window

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

        self.entry.bind("<Return>", lambda e: self.send_msg(to_selected=False))
        tk.Button(bottom, text="Send -> All", command=lambda: self.send_msg(to_selected=False)).pack(side='left', padx=6)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
                # show local IP
        try:
            self.local_ip = self._get_local_ip()
        except:
            self.local_ip = "127.0.0.1"
        self._append_status(f"Local IP: {self.local_ip}")

    def _get_local_ip(self):
        # try to get outbound IP (doesn't actually connect)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip

    def start_listen(self):
        try:
            self.node.start_listening(host='0.0.0.0', port=self.port_var.get())
            self.refresh_peers()
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
        ip = self.ip_var.get()
        port = self.port_var.get()
        try:
            new_id = self.node.connect_to(ip, port)
            self._append_status(f"Connected -> id {new_id}")
            self.refresh_peers()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def refresh_peers(self):
        self.peer_listbox.delete(0, 'end')
        peers = self.node.list_peers()
        for p in peers:
            display = f"{p.id}: {p.addr[0]}:{p.addr[1]}"
            self.peer_listbox.insert('end', display)

    def get_selected_peer_id(self):
        sel = self.peer_listbox.curselection()
        if not sel:
            return None
        text = self.peer_listbox.get(sel[0])
        # format "id: ip:port"
        try:
            id_str = text.split(":")[0]
            return int(id_str)
        except:
            return None

    def disconnect_selected(self):
        pid = self.get_selected_peer_id()
        if pid is None:
            messagebox.showinfo("Info", "Chọn peer để ngắt kết nối")
            return
        try:
            self.node.disconnect_peer(pid)
            self._append_status(f"Disconnected {pid}")
            self.refresh_peers()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def send_msg(self, to_selected=False):
        text = self.entry.get().strip()
        if not text:
            return
        try:
            if to_selected:
                pid = self.get_selected_peer_id()
                if pid is None:
                    messagebox.showinfo("Info", "Chọn peer để gửi")
                    return
                sent = self.node.send_text(text, target_id=pid)
                self._append_chat(f"Me -> {pid}: {text}")
            else:
                sent = self.node.send_text(text, target_id=None)
                self._append_chat(f"Me -> ALL: {text}")
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

    # these are scheduled on main thread via safe wrappers in __init__
    def _on_message_ui(self, msg: dict, conn):
        # show: Peer {id} (ip:port): text
        if msg.get("type") == "msg":
            text = msg.get("text", "")
            self._append_chat(f"Peer {conn.id} ({conn.addr[0]}:{conn.addr[1]}): {text}")
        else:
            self._append_chat(f"[Peer {conn.id}] {msg}")

        # update peer list (in case new connection)
        self.refresh_peers()

    def _append_chat(self, line):

        self.chat.configure(state='normal')
        self.chat.insert('end', line + "\n")
        self.chat.configure(state='disabled')
        self.chat.yview('end')

    def _append_status(self, text):
        self._append_chat(f"[Status] {text}")


    def on_close(self):
        try:
            self.node.close()
        except:
            pass

        self.root.destroy()


        self.root.destroy()

