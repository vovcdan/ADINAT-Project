import socket
import threading
import sys

HOST = '127.0.0.1'
PORT = 8888
SIZE = 1024
FORMAT = 'utf-8'


def receive_message(client_socket):
    username = input("Enter your username: ")
    client_socket.sendall(username.encode())
    from_server = client_socket.recv(SIZE).decode(FORMAT)
    print(from_server)
    while from_server == "425":
        print(f"Username {username} is already taken")
        username = input("Choose another username: ")
        client_socket.sendall(username.encode())
        from_server = client_socket.recv(SIZE).decode(FORMAT)

    while True:
        try:
            from_server = client_socket.recv(SIZE).decode(FORMAT)
            print(f"From Server: {from_server}")
        except ConnectionResetError:
            print("\nDisconnected from server.")
            break


def send_message(client_socket):
    while True:
        try:
            message = input()
            client_socket.sendall(message.encode(FORMAT))
        except ConnectionError:
            pass
    # while True:
    #     try:
    #         message = input()
    #         client_socket.sendall(message.encode(FORMAT))
    #     except ConnectionError:
    #         pass


def get_message():
    pass


if __name__ == '__main__':
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket:
        socket.connect((HOST, PORT))

        threading.Thread(target=receive_message, args=(socket, )).start()
        threading.Thread(target=send_message, args=(socket, )).start()

