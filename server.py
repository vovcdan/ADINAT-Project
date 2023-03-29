import socket
import sys
import threading

global clients


def traiter_client(sock_fille):

    # Wait for the client to send a username
    username = sock_fille.recv(256).decode('utf-8')

    # Check if the username is already in use
    while username in clients.values():
        sock_fille.sendall(str.encode("402\n"))
        username = sock_fille.recv(256).decode('utf-8')

    # Add the client to the list of connected clients
    clients[sock_fille] = username

    # Send a welcome message to the client
    for client in clients.keys():
        client.sendall(str.encode(f"\n{username} connected to the chatroom!\n"))

    while True:
        try:
            # Wait for the client to send a message
            message = sock_fille.recv(256).decode()

            # Check for the /all command
            if message.startswith("/all "):
                # Send the message to all connected clients
                for client in clients.keys():
                    client.sendall(str.encode(f"{username}: {message[5:]}\n"))

        except KeyboardInterrupt:
            sock_fille.close()
            break


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <port>", file=sys.stderr)
        sys.exit(1)

    print("Server is now running.")
    clients = {}

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock_locale:
        sock_locale.bind(("", int(sys.argv[1])))
        sock_locale.listen(4)
        while True:
            try:
                sock_client, adr_client = sock_locale.accept()
                print("Client connected " + str(adr_client))
                state = "login"
                threading.Thread(target=traiter_client, args=(sock_client, )).start()
            except KeyboardInterrupt:
                break
    print("Bye")

    for t in threading.enumerate():
        if t != threading.main_thread():
            t.join()

    sys.exit(0)
