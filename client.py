import socket
import threading


def receive_messages(sock):
    while True:
        try:
            # Receive incoming messages from the server
            message = sock.recv(1024).decode()
            print(message, end="")
        except ConnectionResetError:
            print("\nDisconnected from server.")
            break


def check_username(sock):
    while True:
        code = sock.recv(1024).decode()
        if code == "402":
            print("TEST")
            username = input("Username already taken, choose another: ")
            sock.sendall(str.encode(username))
        else:
            break


def send_messages(sock):
    # Send a username to the server
    username = input("Enter a username: ")
    sock.sendall(str.encode(username))

    t = threading.Thread(target=check_username, args=(sock, ))
    t.start()

    while True:
        # Wait for user to input a message
        message = input()
        if message == "/quit":
            break
        # Send message to server
        sock.sendall(str.encode(message))


if __name__ == "__main__":
    # Connect to server
    host = "localhost"
    port = 8888
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        print("Connected to server.")

        # Start threads to send and receive messages
        receive_thread = threading.Thread(target=receive_messages, args=(sock,))
        receive_thread.start()
        send_thread = threading.Thread(target=send_messages, args=(sock,))
        send_thread.start()

        # Wait for threads to finish
        receive_thread.join()
        send_thread.join()
