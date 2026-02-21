import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", 6000))

print("Listening for discovery...")

while True:
    data, addr = sock.recvfrom(1024)
    print("Got:", data, "from", addr)
    sock.sendto(b"REPLY", addr)
