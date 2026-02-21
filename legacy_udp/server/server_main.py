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

from common.discovery import run_discovery_server
import threading

threading.Thread(target=run_discovery_server, daemon=True).start()

from server.receiver import receive_files

SERVER_PORT = 5001

print("UDP Server running...")
print(f"Listening on port {SERVER_PORT}")

receive_files(SERVER_PORT)
