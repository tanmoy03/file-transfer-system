# import socket
# import os

# HOST = "0.0.0.0"
# PORT = 5001
# BUFFER_SIZE = 4096

# os.makedirs("received_files", exist_ok=True)

# server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# server.bind((HOST, PORT))
# server.listen(1)

# print("Waiting for connection...")

# conn, addr = server.accept()
# print("Connected:", addr)

# filename = conn.recv(BUFFER_SIZE).decode()

# with open("received_files/" + filename, "wb") as f:
#     while True:
#         data = conn.recv(BUFFER_SIZE)
#         if not data:
#             break
#         f.write(data)

# print("File received successfully.")
# conn.close()
# server.close()

from connection import create_udp_socket

SERVER_IP = "0.0.0.0"
SERVER_PORT = 5001

sock = create_udp_socket()
sock.bind((SERVER_IP, SERVER_PORT))

print("UDP Server running...")
print(f"Listening on port {SERVER_PORT}")

while True:
    data, addr = sock.recvfrom(1024)

    message = data.decode()

    print(f"Received from {addr}: {message}")

    # Reply to client
    response = f"ACK: {message}"
    sock.sendto(response.encode(), addr)
