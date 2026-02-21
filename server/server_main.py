import socket
import threading
from typing import Dict, Tuple, Optional

from common.wire import send_json, recv_json

HOST = "0.0.0.0"
PORT = 5001

# username -> (socket, address)
clients: Dict[str, Tuple[socket.socket, Tuple[str, int]]] = {}
clients_lock = threading.Lock()

def handle_client(conn: socket.socket, addr: Tuple[str, int]) -> None:
    username: Optional[str] = None

    try:
        # --- LOGIN first ---
        msg = recv_json(conn)
        if msg.get("type") != "LOGIN" or not msg.get("username"):
            send_json(conn, {"type": "ERROR", "message": "LOGIN required"})
            return

        username = msg["username"].strip()
        if not username:
            send_json(conn, {"type": "ERROR", "message": "Invalid username"})
            return

        with clients_lock:
            if username in clients:
                send_json(conn, {"type": "ERROR", "message": "Username already in use"})
                return
            clients[username] = (conn, addr)

        send_json(conn, {"type": "LOGIN_OK", "username": username})
        print(f"[+] {username} connected from {addr}")

        # --- Main loop ---
        while True:
            msg = recv_json(conn)
            mtype = msg.get("type")

            if mtype == "LIST_USERS":
                with clients_lock:
                    users = sorted(clients.keys())
                send_json(conn, {"type": "USER_LIST", "users": users})

            elif mtype == "QUIT":
                send_json(conn, {"type": "BYE"})
                return

            else:
                send_json(conn, {"type": "ERROR", "message": f"Unknown command: {mtype}"})

    except Exception:
        # disconnected or parse error
        pass
    finally:
        if username:
            with clients_lock:
                cur = clients.get(username)
                if cur and cur[0] is conn:
                    clients.pop(username, None)
            print(f"[-] {username} disconnected")

        try:
            conn.close()
        except Exception:
            pass


def main() -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen()

    print(f"Server running on {HOST}:{PORT}")

    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()