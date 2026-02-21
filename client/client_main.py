import socket
from common.wire import send_json, recv_json

PORT = 5001

def main() -> None:
    server_ip = input("Server IP: ").strip()
    username = input("Username: ").strip()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_ip, PORT))

    # Login
    send_json(sock, {"type": "LOGIN", "username": username})
    resp = recv_json(sock)

    if resp.get("type") != "LOGIN_OK":
        print("Login failed:", resp)
        sock.close()
        return

    print(f"Logged in as {resp.get('username')}. Commands: list, quit")

    while True:
        cmd = input("> ").strip().lower()

        if cmd == "list":
            send_json(sock, {"type": "LIST_USERS"})
            print(recv_json(sock))

        elif cmd == "quit":
            send_json(sock, {"type": "QUIT"})
            print(recv_json(sock))
            sock.close()
            return

        else:
            print("Commands: list, quit")


if __name__ == "__main__":
    main()