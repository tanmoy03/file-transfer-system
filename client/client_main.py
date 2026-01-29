import socket
import os

SERVER_IP = "127.0.0.1"
PORT = 5001
BUFFER_SIZE = 4096

file_path = input("Enter file path: ")
filename = os.path.basename(file_path)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER_IP, PORT))

client.send(filename.encode())

with open(file_path, "rb") as f:
    while True:
        data = f.read(BUFFER_SIZE)
        if not data:
            break
        client.sendall(data)

print("File sent successfully.")
client.close()

