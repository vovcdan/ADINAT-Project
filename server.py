import socket
import sys
import threading

global clients


def process_client(client):

    # Wait for the client to send a username
    username = client.recv(256).decode('utf-8')

    # Check if the username is already in use
    while username in clients.values():
        client.sendall(str.encode("402\n"))
        username = client.recv(256).decode('utf-8')

    client.sendall(str.encode("200\n"))

    # Add the client to the list of connected clients
    clients[client] = username

    # Send a welcome message to the client
    for client in clients.keys():
        client.sendall(str.encode(f"\n{username} connected to the chatroom!\n"))

    while True:
        try:
            # Wait for the client to send a message
            message = client.recv(256).decode()

            # Check for the /all command
            if message.startswith("/msg "):
                client.sendall(str.encode("200"))
                # Send the message to all connected clients
                for client in clients.keys():
                    client.sendall(str.encode(f"{username}: {message[5:]}\n"))

            elif message.startswith("/exit"):
                client.sendall(str.encode("200"))
                client.close()
                for client in clients.keys():
                    client.sendall(str.encode(f"\n{username} left the chatroom.\n"))
                del clients[client]

            elif message.startswith("/afk"):
                client.sendall(str.encode("200"))
                for client in clients.keys():
                    client.sendall(str.encode(f"\n{username} is now afk.\n"))

            elif message.startswith("/users"):
                res = "["
                for client_socket, username in clients:
                    res += username + ", "
                res = res[:-2]
                res = "]"
                client.sendall(str.encode(res))

        except KeyboardInterrupt:
            client.close()
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
                threading.Thread(target=process_client, args=(sock_client,)).start()
            except KeyboardInterrupt:
                break
    print("Bye")

    for t in threading.enumerate():
        if t != threading.main_thread():
            t.join()

    sys.exit(0)
