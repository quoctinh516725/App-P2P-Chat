import json
import struct

# Define a 4-byte big-endian header structure for message length
HEADER = struct.Struct('!I')  # 4 byte big-endian

def pack_message(obj: dict) -> bytes:
    """
    Pack a Python dictionary into a JSON message with a prepended header.
    Ensures encoding in UTF-8, which supports Vietnamese characters.
    
    Args:
        obj (dict): The dictionary to send.
    
    Returns:
        bytes: The packed message in binary format.
    """
    # Convert the dictionary to a JSON string and encode it as UTF-8
    data = json.dumps(obj, ensure_ascii=False).encode('utf-8')  # ensure_ascii=False allows Vietnamese characters
    # Prepend the length of the JSON payload using the header structure
    return HEADER.pack(len(data)) + data

def recv_exact(sock, n: int) -> bytes:
    """
    Receive exactly `n` bytes from the socket.

    Args:
        sock: The socket object.
        n (int): The number of bytes to read.
    
    Returns:
        bytes: The received data.
    
    Raises:
        ConnectionError: If the peer closes the connection unexpectedly.
    """
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Peer closed")
        buf += chunk
    return buf

def read_message(sock) -> dict:
    """
    Read a message from the socket, unpack it, and decode the JSON payload.
    
    Args:
        sock: The socket object.
    
    Returns:
        dict: The decoded JSON object representing the message.
    
    Raises:
        ConnectionError: If the peer closes the connection unexpectedly.
    """
    # Read the 4-byte header to determine the payload length
    (length,) = HEADER.unpack(recv_exact(sock, HEADER.size))
    # Read the exact number of bytes specified in the header
    payload = recv_exact(sock, length)
    # Decode the JSON payload as UTF-8 and return the dictionary
    return json.loads(payload.decode('utf-8'))
