import socket

DISCOVERY_PORT = 6000
DISCOVERY_MESSAGE = "DISCOVER_FTS_SERVER"
RESPONSE_MESSAGE = "FTS_SERVER_HERE"
BUFFER_SIZE = 1024

def run_discovery_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", DISCOVERY_PORT))

    print("Discovery service running...")

    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)

        if data.decode() == DISCOVERY_MESSAGE:
            print("Discovery request from", addr)

            sock.sendto(RESPONSE_MESSAGE.encode(), addr)

def find_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(3)

    message = DISCOVERY_MESSAGE.encode()

    try:
        # Broadcast to entire local network
        sock.sendto(message, ("255.255.255.255", DISCOVERY_PORT))

        data, addr = sock.recvfrom(BUFFER_SIZE)

        if data.decode() == RESPONSE_MESSAGE:
            return addr[0]

    except socket.timeout:
        return None

