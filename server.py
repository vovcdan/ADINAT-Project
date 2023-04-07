import socket
import sys
import threading
import re
from user import User

global clients
FORMAT = 'utf-8'
SIZE = 1024


def broadcast(message):
    for user in clients:
        socket_client = user.socket
        socket_client.sendall(message.encode(FORMAT))


def is_user_connected(socket):
    for user in clients:
        if user.socket == socket:
            return True
    return False


def find_user_by_socket(socket):
    for user in clients:
        if user.socket == socket:
            return user
    return None


def find_user_by_username(username):
    for user in clients:
        if user.username == username:
            return user
    return None


def find_socket(username):
    for user in clients:
        if user.username == username:
            return user.socket
    return None


def check_username_chars(s):
    pattern = r"^[a-zA-Z]+$"
    return re.match(pattern, s) is not None


def remove_user(socket):
    index = None
    for i, user in enumerate(clients):
        if user.socket == socket:
            index = i
            break

    if index is not None:
        del clients[index]


def signup(socket, message):
    # checks if command has the right number of parameters
    if len(message) != 2:
        socket.sendall("403".encode(FORMAT))
        return

    # checks if user is already logged in and if username is already taken
    for user in clients:
        if user.socket == socket and user.state is not None:
            socket.sendall("417".encode(FORMAT))
            return
        if message[1] == user.username:
            socket.sendall("425".encode(FORMAT))
            return

    # checks if username contains special characters or numbers
    if not check_username_chars(message[1]):
        socket.sendall("426".encode(FORMAT))
        return

    signup_from_srv(socket, message[1])


def signup_from_srv(socket, username):
    # Creates a new user and appends it to clients list
    clients.append(User(username, socket))
    broadcast(f"signupFromSrv|{username}")
    socket.sendall("200".encode(FORMAT))


def msg(socket, message):
    command = message[0]
    mess = ' '.join(message[1:])
    total = [command, mess]

    # checks if command has the right number of parameters
    if len(total) != 2:
        socket.sendall("403".encode(FORMAT))
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        socket.sendall("418".encode(FORMAT))
        return

    if mess == "":
        socket.sendall("403".encode(FORMAT))
        return

    # checks if user's state is afk
    if user.state == 'afk':
        socket.sendall("430".encode(FORMAT))
        return

    msg_from_server(user.username, mess, socket)


def msg_from_server(username, message, socket):
    broadcast(f"msgFromServer|{username}|{message}")
    socket.sendall("200".encode(FORMAT))


def exit(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 1:
        socket.sendall("403".encode(FORMAT))
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        socket.sendall("418".encode(FORMAT))
        return

    exit_from_server(user.username, user.socket)


def exit_from_server(username, socket):
    remove_user(socket)
    socket.close()
    broadcast(f"exitFromSrv|{username}")
    socket.sendall("200".encode(FORMAT))


def afk(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 1:
        socket.sendall("403".encode(FORMAT))
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        socket.sendall("418".encode(FORMAT))
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        socket.sendall("415".encode(FORMAT))
        return

    afk_from_server(user)


def afk_from_server(user):
    user.state = 'afk'
    broadcast(f"afkFromSrv|{user.username}")
    user.socket.sendall("200".encode(FORMAT))


def btk(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 1:
        socket.sendall("403".encode(FORMAT))
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        socket.sendall("418".encode(FORMAT))
        return

    # checks if user's state is 'chatting'
    if user.state == 'chatting':
        socket.sendall("416".encode(FORMAT))
        return

    btk_from_server(user)


def btk_from_server(user):
    user.state = 'chatting'
    broadcast(f"btkFromSrv|{user.username}")
    user.socket.sendall("200".encode(FORMAT))


def users(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 1:
        socket.sendall("403".encode(FORMAT))
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        socket.sendall("418".encode(FORMAT))
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        socket.sendall("430".encode(FORMAT))
        return

    users_from_server(socket)


def users_from_server(socket):
    res = "usersFromSrv|["
    for user in clients:
        res += f"{user.username}, "
    res = res[:-2]
    res += "]"
    socket.sendall(res.encode(FORMAT))
    socket.sendall("200".encode(FORMAT))


def ping(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 2:
        socket.sendall("403".encode(FORMAT))
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        socket.sendall("418".encode(FORMAT))
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        socket.sendall("430".encode(FORMAT))
        return

    # checks if username exists
    # we create a new list of usernames and if the username given isn't in that list we send a code error
    if message[1] not in [client.username for client in clients]:
        socket.sendall("402".encode(FORMAT))
        return

    targeted_socket = find_socket(message[1])

    # checks if the username given in the parameter isn't the client himself
    # alternatively we could check if user.username == message[1]
    if targeted_socket == socket:
        socket.sendall("407".encode(FORMAT))
        return

    ping_from_server(socket, targeted_socket, user.username)


def ping_from_server(socket, target_socket, username):
    target_socket.sendall(f"pingFromSrv|{username}".encode(FORMAT))
    socket.sendall("200".encode(FORMAT))


def rename(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 2:
        socket.sendall("403".encode(FORMAT))
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        socket.sendall("418".encode(FORMAT))
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        socket.sendall("430".encode(FORMAT))
        return

    # checks if username exists
    # we create a new list of usernames and if the username given is in that list we send a code error
    if message[1] in [client.username for client in clients]:
        socket.sendall("425".encode(FORMAT))
        return

    # checks if given username does not contain special characters nor numbers
    if not check_username_chars(message[1]):
        socket.sendall("426".encode(FORMAT))
        return

    rename_from_server(user, message[1], socket)


def rename_from_server(user, new_username, socket):
    old_username = user.username
    user.username = new_username

    for user in clients:
        if old_username in user.friends:
            user.remove_friends(old_username)
            user.add_friends(new_username)

        if old_username in user.pending_friends:
            user.remove_pending_friends(old_username)
            user.add_pending_friends(new_username)

    broadcast(f"renameFromSrv|{old_username}|{new_username}")
    socket.sendall("200".encode(FORMAT))


def channel(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 2:
        socket.sendall("403".encode(FORMAT))
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        socket.sendall("418".encode(FORMAT))
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        socket.sendall("430".encode(FORMAT))
        return

    # checks if username exists
    # we create a new list of usernames and if the username given isn't in that list we send a code error
    if message[1] not in [client.username for client in clients]:
        socket.sendall("402".encode(FORMAT))
        return

    targeted_user = find_user_by_username(message[1])

    # checks if the username given in the parameter isn't the client himself
    # alternatively we could check if user.username == message[1]
    if targeted_user.socket == socket:
        socket.sendall("407".encode(FORMAT))
        return

    # checks if the user and targeted user already have a channel open
    if message[1] in user.friends and user.username in targeted_user.friends:
        socket.sendall("404".encode(FORMAT))
        return

    # checks if the user has already sent a channel request to the targeted user
    if user.username in targeted_user.pending_friends:
        socket.sendall("441".encode(FORMAT))
        return

    channel_from_server(user, targeted_user)


def channel_from_server(user, target_user):
    target_user.add_pending_friends(user.username)
    target_user.socket.sendall(f"channelFromSrv|{user.username}".encode(FORMAT))
    user.socket.sendall("200".encode(FORMAT))


def acceptchannel(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 2:
        socket.sendall("403".encode(FORMAT))
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        socket.sendall("418".encode(FORMAT))
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        socket.sendall("430".encode(FORMAT))
        return

    # checks if username exists
    # we create a new list of usernames and if the username given isn't in that list we send a code error
    if message[1] not in [client.username for client in clients]:
        socket.sendall("402".encode(FORMAT))
        return

    targeted_user = find_user_by_username(message[1])

    # checks if the username given in the parameter isn't the client himself
    # alternatively we could check if user.username == message[1]
    if targeted_user.socket == socket:
        socket.sendall("407".encode(FORMAT))
        return

    # checks if the user has any channel requests
    if len(user.pending_friends) == 0:
        socket.sendall("440".encode(FORMAT))
        return

    acceptchannel_from_server(user, targeted_user)


def acceptchannel_from_server(user, target_user):

    # checks if the targeted user is not in the user's friends list
    # if he is not, add him to the friends list
    if target_user.username not in user.friends:
        user.add_friends(target_user.username)

    # checks if the user is not in the targeted user's friends list
    # if he is not, add him to the friends list
    if user.username not in target_user.friends:
        target_user.add_friends(user.username)

    # checks if the user is in the targeted user's pending friends list
    # if he is, remove him from the list
    if user.username in target_user.pending_friends:
        target_user.remove_pending_friends(user.username)

    # checks if the target user is in the user's pendiung friends list
    # if he is, remove him from the list
    if target_user.username in user.pending_friends:
        user.remove_pending_friends(target_user.username)

    target_user.socket.sendall(f"acceptedchannelFromSrv|{user.username}".encode(FORMAT))
    user.socket.sendall("200".encode(FORMAT))


def declinechannel(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 2:
        socket.sendall("403".encode(FORMAT))
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        socket.sendall("418".encode(FORMAT))
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        socket.sendall("430".encode(FORMAT))
        return

    # checks if username exists
    # we create a new list of usernames and if the username given isn't in that list we send a code error
    if message[1] not in [client.username for client in clients]:
        socket.sendall("402".encode(FORMAT))
        return

    targeted_user = find_user_by_username(message[1])

    # checks if the username given in the parameter isn't the client himself
    # alternatively we could check if user.username == message[1]
    if targeted_user.socket == socket:
        socket.sendall("407".encode(FORMAT))
        return

    # checks if the user has any channel requests
    if len(user.pending_friends) == 0:
        socket.sendall("440".encode(FORMAT))
        return

    declinechannel_from_server(user, targeted_user)


def declinechannel_from_server(user, target_user):

    # checks if the user is in the pending friends list of the targeted user
    # if he exists, remove him from the list
    if user.username in target_user.pending_friends:
        target_user.remove_pending_friends(user.username)

    # checks if the targeted user is in the pending friends list of the user
    # if he exists, remove him from the list
    if target_user.username in user.pending_friends:
        user.remove_pending_friends(target_user.username)

    target_user.socket.sendall(f"declinedchannelFromSrv|{user.username}".encode(FORMAT))
    user.socket.sendall("200".encode(FORMAT))


def msgpv(socket, message):
    pass


def msgpv_from_server():
    pass


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
            elif command[0] == 'msgpv':
                msgpv(client_socket, command)
            else:
                client_socket.sendall("400".encode(FORMAT))

        except ConnectionResetError:
            user = find_user_by_socket(client_socket)
            username = user.username
            remove_user(client_socket)
            client_socket.close()
            broadcast(f"exitFromSrv|{username}")
            break


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <port>", file=sys.stderr)
        sys.exit(1)

    print("Server is now running.")
    clients = []

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
