import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

sock.sendto(b"HELLO", ("255.255.255.255", 6000))

print("Sent discovery")

data, addr = sock.recvfrom(1024)
print("Reply from:", addr)