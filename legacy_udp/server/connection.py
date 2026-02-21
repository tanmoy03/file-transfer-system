import socket

BUFFER_SIZE = 1024

def create_udp_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return sock

