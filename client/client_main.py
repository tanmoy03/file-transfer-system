# import socket
# import os

# SERVER_IP = "127.0.0.1"
# PORT = 5001
# BUFFER_SIZE = 4096

# file_path = input("Enter file path: ")
# filename = os.path.basename(file_path)
 
# client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# client.connect((SERVER_IP, PORT))

# client.send(filename.encode())

# with open(file_path, "rb") as f:
#     while True:
#         data = f.read(BUFFER_SIZE)
#         if not data:
#             break
#         client.sendall(data)

# # add try catch block error handling
# # seperate the cli functionality from the file transfer functionality
# # add a popup with a file explorer to choose file to send
# # implement a login system with a server side user database


# print("File sent successfully.")
# client.close()

from client.connection import create_udp_socket

from common.discovery import find_server

print("Searching for server...")

SERVER_IP = find_server()

if SERVER_IP is None:
    print("No server found on network!")
    exit()

print("Server found at:", SERVER_IP)

SERVER_PORT = 5001

sock = create_udp_socket()

while True:
    msg = input("Enter message (or quit): ")

    if msg == "quit":
        break

    sock.sendto(msg.encode(), (SERVER_IP, SERVER_PORT))

    data, addr = sock.recvfrom(1024)

    print("Server replied:", data.decode())
