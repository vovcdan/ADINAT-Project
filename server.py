from datetime import datetime
import socket
import sys
import threading
import re
import atexit
from user import User

global clients
FORMAT = 'utf-8'
SIZE = 1024
can_write = True
mutex = threading.Lock()
writing_condition = threading.Condition(mutex)


def write_to_log(data):
    global can_write
    with mutex:
        writing_condition.wait_for(lambda: can_write)
        can_write = False
        with open('server.log', 'a') as log_file:
            log_file.write(f"[{datetime.now()}] {data}\n")

    with mutex:
        can_write = True
        writing_condition.notify_all()


def on_exit():
    write_to_log(f"Server has stopped.".upper())


atexit.register(on_exit)


def broadcast(message):
    for user in clients:
        socket_client = user.socket
        socket_client.sendall(message.encode(FORMAT))
    write_to_log(f"RESPONSE: {message}")


def unicast(message, socket):
    socket.sendall(message.encode(FORMAT))
    write_to_log(f"RESPONSE: {message}")


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
        unicast("403", socket)
        return

    # checks if user is already logged in and if username is already taken
    for user in clients:
        if user.socket == socket and user.state is not None:
            unicast("417", socket)
            return
        if message[1] == user.username:
            unicast("425", socket)
            return

    # checks if username contains special characters or numbers
    if not check_username_chars(message[1]):
        unicast("426", socket)
        return

    signup_from_srv(socket, message[1])


def signup_from_srv(socket, username):
    # Creates a new user and appends it to clients list
    clients.append(User(username, socket))
    broadcast(f"signupFromSrv|{username}")
    unicast("200", socket)


def msg(socket, message):
    command = message[0]
    mess = ' '.join(message[1:])
    total = [command, mess]

    # checks if command has the right number of parameters
    if len(total) != 2:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        unicast("418", socket)
        return

    if mess == "":
        unicast("403", socket)
        return

    # checks if user's state is afk
    if user.state == 'afk':
        unicast("430", socket)
        return

    msg_from_server(user.username, mess, socket)


def msg_from_server(username, message, socket):
    broadcast(f"msgFromServer|{username}|{message}")
    unicast("200", socket)


def exit(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 1:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    exit_from_server(user.username, user.socket)


def exit_from_server(username, socket):
    remove_user(socket)
    socket.close()
    broadcast(f"exitFromSrv|{username}")


def afk(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 1:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("415", socket)
        return

    afk_from_server(user)


def afk_from_server(user):
    user.state = 'afk'
    broadcast(f"afkFromSrv|{user.username}")
    user.unicast("200", user.socket)


def btk(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 1:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        unicast("418", socket)
        return

    # checks if user's state is 'chatting'
    if user.state == 'chatting':
        unicast("416", socket)
        return

    btk_from_server(user)


def btk_from_server(user):
    user.state = 'chatting'
    broadcast(f"btkFromSrv|{user.username}")
    user.unicast("200", user.socket)


def users(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 1:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    users_from_server(socket)


def users_from_server(socket):
    res = "usersFromSrv|["
    for user in clients:
        res += f"{user.username}, "
    res = res[:-2]
    res += "]"
    unicast(res, socket)
    unicast("200", socket)


def ping(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 2:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    # checks if username exists
    # we create a new list of usernames and if the username given isn't in that list we send a code error
    if message[1] not in [client.username for client in clients]:
        unicast("402", socket)
        return

    targeted_socket = find_socket(message[1])

    # checks if the username given in the parameter isn't the client himself
    # alternatively we could check if user.username == message[1]
    if targeted_socket == socket:
        unicast("407", socket)
        return

    ping_from_server(socket, targeted_socket, user.username)


def ping_from_server(socket, target_socket, username):
    unicast(f"pingFromSrv|{username}", target_socket)
    unicast("200", socket)


def rename(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 2:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    # checks if username exists
    # we create a new list of usernames and if the username given is in that list we send a code error
    if message[1] in [client.username for client in clients]:
        unicast("425", socket)
        return

    # checks if given username does not contain special characters nor numbers
    if not check_username_chars(message[1]):
        unicast("426", socket)
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
    unicast("200", socket)


def channel(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 2:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    # checks if username exists
    # we create a new list of usernames and if the username given isn't in that list we send a code error
    if message[1] not in [client.username for client in clients]:
        unicast("402", socket)
        return

    targeted_user = find_user_by_username(message[1])

    # checks if the username given in the parameter isn't the client himself
    # alternatively we could check if user.username == message[1]
    if targeted_user.socket == socket:
        unicast("407", socket)
        return

    # checks if the user and targeted user already have a channel open
    if message[1] in user.friends and user.username in targeted_user.friends:
        unicast("404", socket)
        return

    # checks if the user has already sent a channel request to the targeted user
    if user.username in targeted_user.pending_friends:
        unicast("441", socket)
        return

    channel_from_server(user, targeted_user)


def channel_from_server(user, target_user):
    target_user.add_pending_friends(user.username)
    unicast(f"channelFromSrv|{user.username}", target_user.socket)
    user.unicast("200", socket)


def acceptchannel(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 2:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    # checks if username exists
    # we create a new list of usernames and if the username given isn't in that list we send a code error
    if message[1] not in [client.username for client in clients]:
        unicast("402", socket)
        return

    targeted_user = find_user_by_username(message[1])

    # checks if the username given in the parameter isn't the client himself
    # alternatively we could check if user.username == message[1]
    if targeted_user.socket == socket:
        unicast("407", socket)
        return

    # checks if the user has any channel requests
    if len(user.pending_friends) == 0:
        unicast("440", socket)
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

    unicast(f"acceptedchannelFromSrv|{user.username}", target_user.socket)
    user.unicast("200", socket)


def declinechannel(socket, message):

    # checks if command has the right number of parameters
    if len(message) != 2:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    # checks if username exists
    # we create a new list of usernames and if the username given isn't in that list we send a code error
    if message[1] not in [client.username for client in clients]:
        unicast("402", socket)
        return

    targeted_user = find_user_by_username(message[1])

    # checks if the username given in the parameter isn't the client himself
    # alternatively we could check if user.username == message[1]
    if targeted_user.socket == socket:
        unicast("407", socket)
        return

    # checks if the user has any channel requests
    if len(user.pending_friends) == 0:
        unicast("440", socket)
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

    unicast(f"declinedchannelFromSrv|{user.username}", target_user.socket)
    unicast("200", user.socket)


def msgpv(socket, message):
    command = message[0]
    target_username = message[1]
    mess = ' '.join(message[2:])
    total = [command, target_username, mess]

    # checks if command has the right number of parameters
    if len(total) != 3:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if user not in clients:
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    # checks if username exists
    # we create a new list of usernames and if the username given isn't in that list we send a code error
    if target_username not in [client.username for client in clients]:
        unicast("402", socket)
        return

    if target_username not in user.friends:
        unicast("421", socket)
        return

    targeted_user = find_user_by_username(target_username)
    msgpv_from_server(socket, user.username, targeted_user.socket, mess)


def msgpv_from_server(socket, username, target_socket, message):
    try:
        unicast(f"msgpvFromSrv|{username}|{message}", target_socket)
        unicast("200", socket)
    except socket.error:
        unicast("500", socket)


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


def help(socket, message):
    # checks if command has the right number of parameters
    if len(message) != 1:
        unicast("403", socket)
        return

    unicast("200", socket)


def process_client(client_socket, client_adress):
    write_to_log(f"{str(client_adress)} HAS CONNECTED.")
    while True:
        try:
            message = client_socket.recv(SIZE).decode(FORMAT)
            if not len(message):
                return
            write_to_log(f"FROM {str(adr_client)} REQUEST: {message.upper()}")
            command = message.split(" ")
            if command[0] == "signup":
                signup(client_socket, command)
            elif command[0] == "help":
                help(client_socket, command)
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
                unicast("400", client_socket)
        except socket.error:
            user = find_user_by_socket(client_socket)
            username = user.username
            remove_user(client_socket)
            write_to_log(f"SUDDEN DISCONNECT FROM {str(adr_client)}")
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
    write_to_log(f"Server has started. Listening on port '{sys.argv[1]}'".upper())
    while True:
        try:
            sock_client, adr_client = sock_locale.accept()
            print(f"Client{str(adr_client)} connected")
            threading.Thread(target=process_client, args=(sock_client, adr_client, )).start()

        except KeyboardInterrupt:
            break
    print("Bye")

    for t in threading.enumerate():
        if t != threading.main_thread():
            t.join()

    sys.exit(0)
