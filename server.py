import socket
import sys
import threading

global clients


def process_client(client):

    while True:
        try:
            message = client.recv(256).decode()

            if message.startswith("/login"):
                username = client.recv(256).decode('utf-8')
                client_state = "logging"
                while username in clients.values():
                    client.sendall(str.encode("402"))
                    username = client.recv(256).decode('utf-8')
                client.sendall(str.encode("200\n"))
                client_state = "chatting"
                clients[client] = (username, client_state)
                for client in clients.keys():
                    client.sendall(str.encode(f"\n{username} connected to the chatroom!\n"))

            elif message.startswith("/msg "):
                if clients[client][1] == "chatting":
                    client.sendall(str.encode("200"))
                    for client in clients.keys():
                        client.sendall(str.encode(f"{clients[client][0]}: {message[5:]}\n"))
                else:
                    client.sendall(str.encode("410"))

            elif message.startswith("/exit"):
                client.sendall(str.encode("200"))
                client.close()
                for client in clients.keys():
                    client.sendall(str.encode(f"\n{clients[client][0]} left the chatroom.\n"))
                del clients[client]

            elif message.startswith("/afk"):
                client.sendall(str.encode("200"))
                clients[client][1] = "afk"
                for client in clients.keys():
                    client.sendall(str.encode(f"\n{clients[client][0]} is now afk.\n"))

            elif message.startswith("/users"):
                res = "["
                for username in clients.values()[0]:
                    res += username + ", "
                res = res[:-2]
                res = "]"
                client.sendall(str.encode(res))

            elif message.startswith("/rename"):
                if message[9:] not in clients.values()[0]:
                    client.sendall(str.encode("402"))
                    for client in clients.keys():
                        client.sendall(str.encode(f"\n{clients[client][0]} changes his name to {message[9:]} .\n"))
                    clients[client][0] = message[9:]
                else :
                    client.sendall(str.encode("425"))

            elif message.startswith("/ping"):
                boo = False
                for client_socket, tuple in clients.items():
                    if tuple[0] == message[5:]:
                        client_socket.sendall(str.encode(f"\n{clients[client][0]} pings you in channel.\n"))
                        boo = True
                        break
                client.sendall(str.encode("200"))
                if boo == False:
                    client.sendall(str.encode("402"))
                    

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
