import json
import socket
import struct
from typing import Any, Dict

HEADER = struct.Struct("!I")  # 4-byte message length (network byte order)


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Socket closed.")
        data += chunk
    return data


def send_json(sock: socket.socket, obj: Dict[str, Any]) -> None:
    payload = json.dumps(obj).encode("utf-8")
    sock.sendall(HEADER.pack(len(payload)))
    sock.sendall(payload)


def recv_json(sock: socket.socket) -> Dict[str, Any]:
    (length,) = HEADER.unpack(_recv_exact(sock, HEADER.size))
    payload = _recv_exact(sock, length)
    return json.loads(payload.decode("utf-8"))


def send_bytes(sock: socket.socket, data: bytes) -> None:
    sock.sendall(data)


def recv_bytes(sock: socket.socket, n: int) -> bytes:
    return _recv_exact(sock, n) 