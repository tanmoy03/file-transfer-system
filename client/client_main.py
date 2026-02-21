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

import os
from common.discovery import find_server
from client.connection import create_udp_socket
from client.sender import send_file

print("Searching for server...")

SERVER_IP = find_server()

if SERVER_IP is None:
    print("Auto-discovery failed.")
    SERVER_IP = input("Enter server IP manually: ")

if not SERVER_IP:
    print("No server available. Exiting.")
    exit()

print("Server found at:", SERVER_IP)

SERVER_PORT = 5001

while True:
    print("\nOptions:")
    print("1 - Send a file")
    print("2 - Quit")

    choice = input("Enter choice: ")

    if choice == "1":

        filename = input("Enter path of file to send: ")

        if not os.path.isfile(filename):
            print("File does not exist:", filename)
            continue

        send_file(filename, SERVER_IP, SERVER_PORT)


    elif choice == "2":
        print("Exiting client.")
        break

    else:
        print("Invalid option.")


# server with mutliple clients where clients can login and send files to the server. The server can handle multiple clients at the same time and store the files in a directory named after the client. The server can also keep a log of all the files received from each client.
# server then sends out files to desired clients on request. 

