import socket

DISCOVERY_PORT = 6000
DISCOVERY_MESSAGE = "DISCOVER_FILE_SERVER"
RESPONSE_MESSAGE = "FILE_SERVER_HERE"


def run_discovery_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", DISCOVERY_PORT))

    print("Discovery service running...")

    while True:
        data, addr = sock.recvfrom(1024)

        if data.decode() == DISCOVERY_MESSAGE:
            sock.sendto(RESPONSE_MESSAGE.encode(), addr)


def find_server(timeout=3):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)

    sock.sendto(DISCOVERY_MESSAGE.encode(), ("<broadcast>", DISCOVERY_PORT))

    try:
        data, addr = sock.recvfrom(1024)
        if data.decode() == RESPONSE_MESSAGE:
            return addr[0]
    except socket.timeout:
        return None