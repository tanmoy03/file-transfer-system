import socket
from common.protocol import *

def receive_files(server_port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", server_port))

    print("Waiting for file...")

    filename = None
    file = None

    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)

        # Extract packet type first
        parts = data.split(b"|", 2)

        try:
            packet_type = int(parts[0].decode())
        except:
            continue

        # ----- FILENAME -----
        if packet_type == TYPE_FILENAME:
            filename = parts[1].decode()
            file = open("received_" + filename, "wb")

            print("Receiving file:", filename)

            sock.sendto(f"{TYPE_ACK}|0".encode(), addr)

        # ----- DATA -----
        elif packet_type == TYPE_DATA:
            seq = parts[1].decode()
            content = parts[2]

            file.write(content)

            sock.sendto(f"{TYPE_ACK}|{seq}".encode(), addr)

        # ----- EOF -----
        elif packet_type == TYPE_EOF:
            file.close()
            print("File received successfully")
            break
