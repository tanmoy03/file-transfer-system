import socket
import os
from common.protocol import *

def send_file(filename, server_ip, server_port):
    if not os.path.isfile(filename):
        print("Invalid file path:", filename)
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)

    addr = (server_ip, server_port)

    # --- Send filename first ---
    packet = f"{TYPE_FILENAME}|{os.path.basename(filename)}"
    sock.sendto(packet.encode(), addr)

    try:
        sock.recvfrom(BUFFER_SIZE)   # wait for ACK
    except:
        print("No ACK for filename")
        return

    seq = 0

    with open(filename, "rb") as f:
        while True:
            chunk = f.read(512)

            if not chunk:
                break

            data_packet = f"{TYPE_DATA}|{seq}|".encode() + chunk

            while True:
                sock.sendto(data_packet, addr)

                try:
                    data, _ = sock.recvfrom(BUFFER_SIZE)
                    if data.decode() == f"{TYPE_ACK}|{seq}":
                        break
                except:
                    print("Resending packet", seq)

            seq += 1

    # --- Send EOF ---
    sock.sendto(f"{TYPE_EOF}".encode(), addr)
    print("File sent successfully")