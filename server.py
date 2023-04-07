import socket
import sys
import threading
import re

global clients
FORMAT = 'utf-8'
SIZE = 1024


def broadcast(message):
    for username, info in clients.items():
        socket_client = info['socket']
        socket_client.sendall(message.encode(FORMAT))


def is_user_connected(socket):
    if socket in [info['socket'] for info in clients.values()]:
        return True
    return False


def get_username_from_socket(socket):
    username = None
    for name, info in clients.items():
        if info['socket'] == socket:
            username = name
    return username


def get_friends_from_socket(socket):
    friends = []
    for name, info in clients.items():
        if info['socket'] == socket:
            friends = info['friends']
    return friends


def get_pending_friends_from_socket(socket):
    pending = []
    for name, info in clients.items():
        if info['socket'] == socket:
            pending = info['pending_friends']
    return pending


def get_pending_files_from_socket(socket):
    pending = []
    for name, info in clients.items():
        if info['socket'] == socket:
            pending = info['pending_files']
    return pending


def get_state_from_socket(socket):
    state = None
    for name, info in clients.items():
        if info['socket'] == socket:
            state = info['state']
    return state


def check_username_chars(s):
    pattern = r"^[a-zA-Z]+$"
    return re.match(pattern, s) is not None


def signup(socket, message):
    if len(message) != 2:
        socket.sendall("403".encode(FORMAT))
        return

    for user, dic in clients.items():
        if dic['socket'] == socket and dic['state'] is not None:
            socket.sendall("417".encode(FORMAT))
            return

    if message[1] in clients.keys():
        socket.sendall("425".encode(FORMAT))
        return

    if not check_username_chars(message[1]):
        socket.sendall("426".encode(FORMAT))
        return

    signup_from_srv(socket, message[1])
    socket.sendall("200".encode(FORMAT))


def signup_from_srv(socket, username):
    clients[username] = {'socket': socket,
                         'state': 'chatting',
                         'friends': [],
                         'pending_friends': [],
                         'pending_files': []}
    broadcast(f"signupFromSrv|{username}")


def msg(socket, message):
    command = message[0]
    mess = ' '.join(message[1:])
    total = [command, mess]

    if len(total) != 2:
        socket.sendall("403".encode(FORMAT))
        return

    if not is_user_connected(socket):
        socket.sendall("418".encode(FORMAT))
        return

    if mess == "":
        socket.sendall("403".encode(FORMAT))
        return

    username = get_username_from_socket(socket)

    if clients[username]['state'] == 'afk':
        socket.sendall("430".encode(FORMAT))
        return

    if clients[username]['state'] == 'chatting':
        msg_from_server(username, mess)
        socket.sendall("200".encode(FORMAT))


def msg_from_server(username, message):
    broadcast(f"msgFromServer|{username}|{message}")


def exit(socket, message):
    if len(message) != 1:
        socket.sendall("403".encode(FORMAT))
        return

    if not is_user_connected(socket):
        socket.sendall("418".encode(FORMAT))
        return

    exit_from_server(socket)
    socket.sendall("200".encode(FORMAT))


def exit_from_server(socket):
    username = get_username_from_socket(socket)
    local_sock = socket
    del clients[username]
    local_sock.close()
    broadcast(f"exitFromSrv|{username}")


def afk(socket, message):
    if len(message) != 1:
        socket.sendall("403".encode(FORMAT))
        return

    if not is_user_connected(socket):
        socket.sendall("418".encode(FORMAT))
        return

    if get_state_from_socket(socket) == 'afk':
        socket.sendall("415".encode(FORMAT))
        return

    afk_from_server(socket)
    socket.sendall("200".encode(FORMAT))


def afk_from_server(socket):
    username = get_username_from_socket(socket)
    clients[username]['state'] = 'afk'
    broadcast(f"afkFromSrv|{username}")


def btk(socket, message):
    if len(message) != 1:
        socket.sendall("403".encode(FORMAT))
        return

    if not is_user_connected(socket):
        socket.sendall("418".encode(FORMAT))
        return

    if get_state_from_socket(socket) == 'chatting':
        socket.sendall("416".encode(FORMAT))
        return

    btk_from_server(socket)
    socket.sendall("200".encode(FORMAT))


def btk_from_server(socket):
    username = get_username_from_socket(socket)
    clients[username]['state'] = 'chatting'
    broadcast(f"btkFromSrv|{username}")


def users(socket, message):
    if len(message) != 1:
        socket.sendall("403".encode(FORMAT))
        return

    if not is_user_connected(socket):
        socket.sendall("418".encode(FORMAT))
        return

    if get_state_from_socket(socket) == 'afk':
        socket.sendall("430".encode(FORMAT))
        return

    users_from_server(socket)
    socket.sendall("200".encode(FORMAT))


def users_from_server(socket):
    res = "usersFromSrv|["
    for username in clients.keys():
        res += f"{username}, "
    res = res[:-2]
    res += "]"
    socket.sendall(res.encode(FORMAT))


def ping(socket, message):
    if len(message) != 2:
        socket.sendall("403".encode(FORMAT))
        return

    if not is_user_connected(socket):
        socket.sendall("418".encode(FORMAT))
        return

    if get_state_from_socket(socket) == 'afk':
        socket.sendall("430".encode(FORMAT))
        return

    if message[1] not in clients.keys():
        socket.sendall("406".encode(FORMAT))
        return

    targeted_socket = clients[message[1]]['socket']

    if targeted_socket == socket:
        socket.sendall("407".encode(FORMAT))
        return

    ping_from_server(socket, targeted_socket)
    socket.sendall("200".encode(FORMAT))


def ping_from_server(socket, target_socket):
    username = get_username_from_socket(socket)
    target_socket.sendall(f"pingFromSrv|{username}".encode(FORMAT))


def rename(socket, message):
    if len(message) != 2:
        socket.sendall("403".encode(FORMAT))
        return

    if not is_user_connected(socket):
        socket.sendall("418".encode(FORMAT))
        return

    if get_state_from_socket(socket) == 'afk':
        socket.sendall("430".encode(FORMAT))
        return

    if message[1] in clients.keys():
        socket.sendall("425".encode(FORMAT))
        return

    if not check_username_chars(message[1]):
        socket.sendall("426".encode(FORMAT))
        return

    rename_from_server(socket, message[1])
    socket.sendall("200".encode(FORMAT))


def rename_from_server(socket, new_username):
    username = get_username_from_socket(socket)
    friends = get_friends_from_socket(socket)
    pending_friends = get_pending_friends_from_socket(socket)
    pending_files = get_pending_files_from_socket(socket)
    clients[new_username] = {'socket': socket,
                             'state': 'chatting',
                             'friends': friends,
                             'pending_friends': pending_friends,
                             'pending_files': pending_files}
    del clients[username]
    broadcast(f"renameFromSrv|{username}|{new_username}")


def channel(socket, message):
    if len(message) != 2:
        socket.sendall("403".encode(FORMAT))
        return

    if not is_user_connected(socket):
        socket.sendall("418".encode(FORMAT))
        return

    if get_state_from_socket(socket) == 'afk':
        socket.sendall("430".encode(FORMAT))
        return

    if message[1] not in clients.keys():
        socket.sendall("406".encode(FORMAT))
        return

    targeted_socket = clients[message[1]]['socket']

    if targeted_socket == socket:
        socket.sendall("407".encode(FORMAT))
        return

    username = get_username_from_socket(socket)
    friends = get_friends_from_socket(socket)
    targeted_friends = get_friends_from_socket(targeted_socket)

    if message[1] in friends or username in targeted_friends:
        socket.sendall("440".encode(FORMAT))
        return

    channel_from_server(socket, targeted_socket, username, message[1], friends)
    socket.sendall("200".encode(FORMAT))


def channel_from_server(socket, target_socket, username, target_username, friends):
    targeted_pending_friends = get_pending_friends_from_socket(target_socket)
    targeted_pending_friends.append(username)
    target_socket.sendall(f"channelFromSrv|{username}".encode(FORMAT))


def acceptchannel(socket, message):
    if len(message) != 2:
        socket.sendall("403".encode(FORMAT))
        return

    if not is_user_connected(socket):
        socket.sendall("418".encode(FORMAT))
        return

    if get_state_from_socket(socket) == 'afk':
        socket.sendall("430".encode(FORMAT))
        return

    if message[1] not in clients.keys():
        socket.sendall("406".encode(FORMAT))
        return

    targeted_socket = clients[message[1]]['socket']

    if targeted_socket == socket:
        socket.sendall("407".encode(FORMAT))
        return

    pending_friends = get_pending_friends_from_socket(socket)
    username = get_username_from_socket(socket)
    targeted_pending_friends = get_pending_friends_from_socket(targeted_socket)

    if len(pending_friends) == 0:
        socket.sendall("440".encode(FORMAT))
        return

    acceptchannel_from_server(socket, username, message[1], targeted_socket, targeted_pending_friends, pending_friends)
    socket.sendall("200".encode(FORMAT))


def acceptchannel_from_server(socket, username, target_username, target_socket, target_pending_friends, pending_friends):
    try:
        target_friends = get_friends_from_socket(target_socket)
        friends = get_friends_from_socket(socket)
        target_friends.append(username)
        friends.append(target_username)
        if username in target_pending_friends:
            target_pending_friends.remove(username)
        pending_friends.remove(target_username)
        socket.sendall(f"acceptchannelFromSrv|{target_username}".encode(FORMAT))
    except Exception as e:
        print(e)
        socket.sendall("500".encode(FORMAT))
        target_socket.sendall("500".encode(FORMAT))



def declinechannel(socket, message):
    if len(message) != 2:
        socket.sendall("403".encode(FORMAT))
        return

    if not is_user_connected(socket):
        socket.sendall("418".encode(FORMAT))
        return

    if get_state_from_socket(socket) == 'afk':
        socket.sendall("430".encode(FORMAT))
        return

    if message[1] not in clients.keys():
        socket.sendall("406".encode(FORMAT))
        return

    targeted_socket = clients[message[1]]['socket']

    if targeted_socket == socket:
        socket.sendall("407".encode(FORMAT))
        return

    pending_friends = get_pending_friends_from_socket(socket)
    username = get_username_from_socket(socket)
    targeted_pending_friends = get_pending_friends_from_socket(targeted_socket)

    if len(pending_friends) == 0:
        socket.sendall("440".encode(FORMAT))
        return

    declinechannel_from_server(socket,targeted_socket, username, message[1], pending_friends, targeted_pending_friends)


def declinechannel_from_server(socket, target_socket, username, target_username, pending_friends, target_pending_friends):
    try:
        pending_friends.remove(target_username)
        if username in target_pending_friends:
            target_pending_friends.remove(username)
        socket.sendall(f"declinechannelFromSrv|{target_username}".encode(FORMAT))
    except Exception as e:
        print(e)
        socket.sendall("500".encode(FORMAT))
        target_socket.sendall("500".encode(FORMAT))


def sharefile(socket, message):
    pass


def sharefile_from_server(socket):
    pass


def acceptfile(socket, message):
    pass


def acceptfile_from_server(socket):
    pass


def declinefile(socket, message):
    pass


def declinefile_from_server():
    pass


def process_client(client_socket):
    while True:
        try:
            message = client_socket.recv(SIZE).decode(FORMAT)
            command = message.split(" ")
            if command[0] == "signup":
                signup(client_socket, command)
            elif command[0] == "msg":
                msg(client_socket, command)
            elif command[0] == "exit":  # NOT WORKING AS INTENDED
                exit(client_socket, command)
            elif command[0] == "afk":
                afk(client_socket, command)
            elif command[0] == "btk":
                btk(client_socket, command)
            elif command[0] == "users":
                users(client_socket, command)
            elif command[0] == "ping":
                ping(client_socket, command)
            elif command[0] == "channel":
                channel(client_socket, command)
            elif command[0] == "rename":
                rename(client_socket, command)
            elif command[0] == "acceptchannel":
                acceptchannel(client_socket, command)
            elif command[0] == "declinechannel":
                declinechannel(client_socket, command)
            elif command[0] == "sharefile":
                sharefile(client_socket, command)
            elif command[0] == "acceptfile":
                acceptfile(client_socket, command)
            elif command[0] == "declinefile":
                declinefile(client_socket, command)
            else:
                client_socket.sendall("400".encode(FORMAT))

        except ConnectionResetError:
            username = get_username_from_socket(client_socket)
            del clients[username]
            client_socket.close()
            broadcast(f"exitFromSrv|{username}")
            break


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <port>", file=sys.stderr)
        sys.exit(1)

    print("Server is now running.")
    clients = {}
    usernames = []

    sock_locale = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
