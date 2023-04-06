import socket
import sys
import threading

global clients
FORMAT = 'utf-8'
SIZE = 1024


def broadcast(message):
    for username, info in clients.items():
        socket_client = info['socket']
        socket_client.sendall(message.encode(FORMAT))


def process_client(client_socket):
    username = None
    while True:
        try:
            message = client_socket.recv(SIZE).decode(FORMAT)
            command = message.split(" ", 1)

            if command[0] == "signup":
                if command[1] in clients.keys():
                    client_socket.sendall("425".encode(FORMAT))
                else:
                    client_socket.sendall("200".encode(FORMAT))
                    username = command[1]
                    clients[username] = {'socket': client_socket, 'state': 'chatting'}
                    broadcast(f"{username} has connected to the chatroom!")

            elif command[0] == "msg":
                if clients[username]['state'] == 'chatting':
                    client_socket.sendall("200".encode(FORMAT))
                    mess = f"{username}: "
                    for mot in command[1:]:
                        mess += mot + " "
                    mess = mess[:-1]
                    broadcast(mess)
                else:
                    client_socket.sendall("410".encode(FORMAT))

            elif command[0] == "exit":
                client_socket.sendall("200".encode())
                client_socket.close()
                broadcast(f"{username} has left the chatroom!")
                del clients[username]

            elif command[0] == "afk":
                if clients[username]['state'] == 'chatting':
                    client_socket.sendall("200".encode(FORMAT))
                    clients[username]['state'] = 'afk'
                    broadcast(f"{username} is now away from keyboard!")
                else:
                    client_socket.sendall("409".encode(FORMAT))

            elif command[0] == "btk":
                if clients[username]['state'] == 'afk':
                    client_socket.sendall("200".encode(FORMAT))
                    clients[username]['state'] = 'chatting'
                    broadcast(f"{username} is now back to keyboard!")
                else:
                    client_socket.sendall("409".encode(FORMAT))

            elif command[0] == "users":
                res = "["
                for username in clients.keys():
                    res += username + ", "
                res = res[:-2]
                res += "]"
                client_socket.sendall(res.encode(FORMAT))

            elif command[0] == "ping":
                if command[1] in clients.keys():
                    client_socket.sendall("402".encode(FORMAT))
                    continue
                pinged_client = clients[command[1]]['socket']
                pinged_client.sendall(f"{username} is pinging you!")
                client_socket.sendall("200".encode(FORMAT))

            elif command[0] == "channel":
                if command[1] in clients.keys():
                    client_socket.sendall("402".encode(FORMAT))
                    continue
                pinged_client = clients[command[1]]['socket']
                pinged_client.sendall(f"{username} wants to private chat with you. Do you accept?")

            else:
                client_socket.sendall(str.encode("No command found.\n"))

        except ConnectionError:
            del clients[username]
            client_socket.close()
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
                threading.Thread(target=process_client, args=(sock_client,)).start()
            except KeyboardInterrupt:
                break
    print("Bye")

    for t in threading.enumerate():
        if t != threading.main_thread():
            t.join()

    sys.exit(0)
