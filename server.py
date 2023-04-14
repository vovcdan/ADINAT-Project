import os
from datetime import datetime
import socket as s
import sys
import threading
import signal
import yaml
from user import User

global clients
LOG_FILE = ''
SERVER_HOST = ''
SERVER_PORT = 0
FORMAT = 'utf-8'
SIZE = 1024
can_write = True
can_access_data = True
mutex_access_data = threading.Lock()
mutex = threading.Lock()
writing_condition = threading.Condition(mutex)
accessing_data_condition = threading.Condition(mutex_access_data)


def read_from_config():
    """
    Reads from the configuration file the necessary data :
        the address for the server, the port and the name of the log file
    """
    with open('adinat_config.yaml', 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.FullLoader)

    global SERVER_HOST
    SERVER_HOST = config['server']['host']
    global SERVER_PORT
    SERVER_PORT = config['server']['port']
    global LOG_FILE
    LOG_FILE = config['log']['file']


def write_to_log(data):
    """
    Writes to the log file with the data passed in.
    This function assures that the file isn't opened by 2 or more threads at the same time.

    :param data: The data to be written in the log file
    """
    global can_write
    global LOG_FILE
    # checks if the thread is allowed to write to the log file
    with mutex:
        writing_condition.wait_for(lambda: can_write)
        # retain lock
        can_write = False
        # write to log file
        with open(LOG_FILE, 'a') as file:
            file.write(f"[{datetime.now()}] {data}\n")

    with mutex:
        # release lock
        can_write = True
        writing_condition.notify_all()


def on_exit():
    """
    Writes to log once the server is quitting.
    """
    write_to_log(f"Server has stopped.".upper())


signal.signal(signal.SIGTERM, on_exit)


def broadcast(message):
    """
    Sends a message to all the connected clients through their sockets.
    This function also writes to the log file the message sent.

    :param message: The message to be sent.
    :return:
    """
    global can_access_data
    with mutex_access_data:
        accessing_data_condition.wait_for(lambda: can_access_data)
        can_access_data = False
        for user in clients:
            socket_client = user.socket
            socket_client.sendall(message.encode(FORMAT))
        write_to_log(f"RESPONSE: {message}")

    with mutex_access_data:
        can_access_data = True
        accessing_data_condition.notify_all()


def unicast(message, socket):
    """
    Sends a message to a unique connected client through his socket.
    This function also writes to the log file the message sent.

    :param message: Message to be sent.
    :param socket: The socket of the user.
    """
    socket.sendall(message.encode(FORMAT))
    write_to_log(f"RESPONSE: {message}")


def is_user_connected(socket):
    """
    Checks if a user is connected based on his socket.

    :param socket: The socket of the user.
    :return boolean
    """
    connected = False
    global can_access_data
    with mutex_access_data:
        accessing_data_condition.wait_for(lambda: can_access_data)
        can_access_data = False
        for user in clients:
            if user.socket == socket:
                connected = True
                break

    with mutex_access_data:
        can_access_data = True
        accessing_data_condition.notify_all()
    return connected


def is_user_in_clients_list(user):
    """
    Checks if a user is connected based on the user object in the clients list.

    :param user: An user.
    :return boolean
    """
    connected = False
    global can_access_data
    with mutex_access_data:
        accessing_data_condition.wait_for(lambda: can_access_data)
        can_access_data = False
        if user in clients:
            connected = True

    with mutex_access_data:
        can_access_data = True
        accessing_data_condition.notify_all()
    return connected


def is_username_connected(username):
    """
    Checks if a user is connected based on his username.

    :param username: An username.
    :return boolean
    """
    connected = False
    global can_access_data
    with mutex_access_data:
        accessing_data_condition.wait_for(lambda: can_access_data)
        can_access_data = False
        # we create a new list of usernames and if the username given is in that list we send a code error
        if username in [client.username for client in clients]:
            connected = True

    with mutex_access_data:
        can_access_data = True
        accessing_data_condition.notify_all()
    return connected


def find_user_by_socket(socket):
    """
    Finds a unique user based on his socket.

    :param socket: The socket of the user.
    :return user
    """
    get_user = None
    global can_access_data
    with mutex_access_data:
        accessing_data_condition.wait_for(lambda: can_access_data)
        can_access_data = False
        for user in clients:
            if user.socket == socket:
                get_user = user
                break

    with mutex_access_data:
        can_access_data = True
        accessing_data_condition.notify_all()
    return get_user


def find_user_by_username(username):
    """
    Finds a unique user based on his username.

    :param username: Username of the user.
    :return user
    """
    get_user = None
    global can_access_data
    with mutex_access_data:
        accessing_data_condition.wait_for(lambda: can_access_data)
        can_access_data = False
        for user in clients:
            if user.username == username:
                get_user = user
                break

    with mutex_access_data:
        can_access_data = True
        accessing_data_condition.notify_all()
    return get_user


def find_socket(username):
    """
    Finds a unique socket attached to a user based on his username.

    :param username: Username of the user.
    :return socket
    """
    get_socket = None
    global can_access_data
    with mutex_access_data:
        accessing_data_condition.wait_for(lambda: can_access_data)
        can_access_data = False
        for user in clients:
            if user.username == username:
                get_socket = user.socket
                break

    with mutex_access_data:
        can_access_data = True
        accessing_data_condition.notify_all()
    return get_socket


def remove_user(socket):
    """
    Removes an unique user based on his socket.

    :param socket: Socket of the user.
    """
    global can_access_data
    with mutex_access_data:
        accessing_data_condition.wait_for(lambda: can_access_data)
        can_access_data = False
        index = None
        for i, user in enumerate(clients):
            if user.socket == socket:
                index = i
                break

        if index is not None:
            del clients[index]

    with mutex_access_data:
        can_access_data = True
        accessing_data_condition.notify_all()


def signup(socket, message):
    """
    Checks if the user is able to sign up into the chatroom.
    The user must:
        1. Enter the correct amount of parameters.
        2. Enter an username that has not been used by another user.
        3. Enter an username that doesn't contain any special characters and/or numbers.
        4. Not be logged in.

    In the event that one of these constraints are not met, the user will receive an error code and the function will stop.

    :param socket: Socket of the user.
    :param message: Message sent by the user containing:
                    1. The name of the command.
                    2. An username.
    """
    # checks if command has the right number of parameters
    if len(message) != 2:
        unicast("403", socket)
        return

    global can_access_data
    with mutex_access_data:
        accessing_data_condition.wait_for(lambda: can_access_data)
        can_access_data = False
    # checks if user is already logged in and if username is already taken
        for user in clients:
            if user.socket == socket and user.state is not None:
                can_access_data = True
                accessing_data_condition.notify_all()
                unicast("417", socket)
                return
            if message[1] == user.username:
                can_access_data = True
                accessing_data_condition.notify_all()
                unicast("425", socket)
                return

        can_access_data = True
        accessing_data_condition.notify_all()

    # checks if username contains special characters or numbers
    if not message[1].isalpha():
        unicast("426", socket)
        return

    # calls the function to process the command for the user
    signup_from_srv(socket, message[1])


def signup_from_srv(socket, username):
    """
    Creates a new user and appends it to clients list.

    :param socket: Socket of the user.
    :param username: Username of the user.
    """
    try:
        global can_access_data
        with mutex_access_data:
            accessing_data_condition.wait_for(lambda: can_access_data)
            can_access_data = False
            clients.append(User(username, socket))

        with mutex_access_data:
            can_access_data = True
            accessing_data_condition.notify_all()
        broadcast(f"signupFromSrv|{username}")
        unicast("200", socket)
    except s.error:
        unicast("500", socket)


def msg(socket, message):
    """
    Checks if the user is able to send a message to all the other users.
    The user must:
        1. Enter the correct amount of parameters.
        2. Be in a 'btk'/'chatting' state.
        4. Be logged in.

    In the event that one of these constraints are not met, the user will receive an error code and the function will stop.

    :param socket: Socket of the user.
    :param message: Message sent by the user containing:
                    1. The name of the command.
                    2. The message to be sent to the other users.
    """
    command = message[0]
    mess = ' '.join(message[1:])
    total = [command, mess]

    # checks if command has the right number of parameters
    if len(total) != 2:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if not is_user_in_clients_list(user):
        unicast("418", socket)
        return

    if mess == "":
        unicast("403", socket)
        return

    # checks if user's state is afk
    if user.state == 'afk':
        unicast("430", socket)
        return

    # calls the function to process the command for the user
    msg_from_server(user.username, mess, socket)


def msg_from_server(username, message, socket):
    """
    Sends the message to all the other users.

    :param username: Username of the user sending the message.
    :param message: Message of the user.
    :param socket: Socket of the user.
    """
    try:
        broadcast(f"msgFromSrv|{username}|{message}")
        unicast("200", socket)
    except s.error:
        unicast("500", socket)


def exit(socket, message):
    """
    Checks if the user is able to exit the server.
    The user must:
        1. Enter the correct amount of parameters.

    In the event that one of these constraints are not met, the user will receive an error code and the function will stop.

    :param socket: Socket of the user.
    :param message: Message sent by the user containing:
                    1. The name of the command.
    """
    # checks if command has the right number of parameters
    if len(message) != 1:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    if user is not None:
        # calls the function to process the command for the user
        exit_from_server(user.username, socket)
    else:
        exit_from_server(None, socket)


def exit_from_server(username, socket):
    """
    Removes the user from the server, terminates his connection and informs the other users that the user has left.

    :param username: Username of the user that left.
    :param socket: Socket of the user that left.
    """
    try:
        if username is not None:
            remove_user(socket)
        socket.close()
        if username is not None:
            broadcast(f"exitedFromSrv|{username}")
        print(f"Client {str(adr_client)} disconnected.")
    except s.error:
        unicast("500", socket)


def afk(socket, message):
    """
    Checks if the user is able to get into the 'afk' state.
    The user must:
        1. Enter the correct amount of parameters.
        2. Must be logged in.
        3. Not be in the 'afk' state.

    In the event that one of these constraints are not met, the user will receive an error code and the function will stop.

    :param socket: Socket of the user.
    :param message: Message sent by the user containing:
                    1. The name of the command.
    """
    # checks if command has the right number of parameters
    if len(message) != 1:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if not is_user_in_clients_list(user):
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("415", socket)
        return

    # calls the function to process the command for the user
    afk_from_server(user)


def afk_from_server(user):
    """
    Changes an user's state from 'btk'/'chatting' to 'afk' and informs the other users the new state of the user.

    :param user: User object containing all his details (socket, username, state etc.)
    """
    try:
        user.state = 'afk'
        broadcast(f"afkFromSrv|{user.username}")
        unicast("200", user.socket)
    except s.error:
        unicast("500", user.socket)


def btk(socket, message):
    """
    Checks if the user is able to get into the 'btk'/'chatting' state.
    The user must:
        1. Enter the correct amount of parameters.
        2. Must be logged in.
        3. Not be in the 'btk' state.

    In the event that one of these constraints are not met, the user will receive an error code and the function will stop.

    :param socket: Socket of the user.
    :param message: Message sent by the user containing:
                    1. The name of the command.
    """
    # checks if command has the right number of parameters
    if len(message) != 1:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if not is_user_in_clients_list(user):
        unicast("418", socket)
        return

    # checks if user's state is 'chatting'
    if user.state == 'chatting':
        unicast("416", socket)
        return

    btk_from_server(user)


def btk_from_server(user):
    """
    Changes an user's state from 'afk' to 'btk'/'chatting' and informs the other users the new state of the user.

    :param user: User object containing all his details (socket, username, state etc.)
    """
    try:
        user.state = 'chatting'
        broadcast(f"btkFromSrv|{user.username}")
        unicast("200", user.socket)
    except s.error:
        unicast("500", user.socket)


def users(socket, message):
    """
    Checks if the user is able to get the list of the connected users.
    The user must:
        1. Enter the correct amount of parameters.
        2. Must be logged in.
        3. Not be in the 'afk' state.

    In the event that one of these constraints are not met, the user will receive an error code and the function will stop.

    :param socket: Socket of the user.
    :param message: Message sent by the user containing:
                    1. The name of the command.
    """
    # checks if command has the right number of parameters
    if len(message) != 1:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if not is_user_in_clients_list(user):
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    users_from_server(socket)


def users_from_server(socket):
    """
    Sends a list of connected users to the user.

    :param socket: Socket of the user.
    """
    try:
        global can_access_data
        with mutex_access_data:
            accessing_data_condition.wait_for(lambda: can_access_data)
            can_access_data = False
            res = "usersFromSrv|["
            for user in clients:
                res += f"{user.username}, "
            res = res[:-2]
            res += "]"

        with mutex_access_data:
            can_access_data = True
            accessing_data_condition.notify_all()

        unicast(res, socket)
        unicast("200", socket)
    except s.error:
        unicast("500", socket)


def ping(socket, message):
    """
    Checks if the user is able to ping another user.
    The user must:
        1. Enter the correct amount of parameters.
        2. Must be logged in.
        3. Not be in the 'afk' state.
        4. Enter an username that is attached to an user and online.
        5. Not enter his username.

    In the event that one of these constraints are not met, the user will receive an error code and the function will stop.

    :param socket: Socket of the user.
    :param message: Message sent by the user containing:
                    1. The name of the command.
                    2. The username of the user to be pinged.
    """
    # checks if command has the right number of parameters
    if len(message) != 2:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if not is_user_in_clients_list(user):
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    # checks if username exists
    if not is_username_connected(message[1]):
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
    """
    Pings a unique user.
    The pinged user receives a message with the username who pinged him.

    :param socket: Socket of the user.
    :param target_socket: Socket of the pinged user.
    :param username: Username of the user.
    :return:
    """
    try:
        unicast(f"pingFromSrv|{username}", target_socket)
        unicast("200", socket)
    except s.error:
        unicast("500", socket)


def rename(socket, message):
    """
    Checks if the user is able to change his username.
    The user must:
        1. Enter the correct amount of parameters.
        2. Must be logged in.
        3. Not be in the 'afk' state.
        4. Enter an username that is not taken by another user.
        5. Enter an username that does not contain any special characters and/or numbers.

    In the event that one of these constraints are not met, the user will receive an error code and the function will stop.

    :param socket: Socket of the user.
    :param message: Message sent by the user containing:
                    1. The name of the command.
                    2. The new username.
    """
    # checks if command has the right number of parameters
    if len(message) != 2:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if not is_user_in_clients_list(user):
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    # checks if username exists
    if is_username_connected(message[1]):
        unicast("425", socket)
        return

    # checks if given username does not contain special characters nor numbers
    if not message[1].isalpha():
        unicast("426", socket)
        return

    rename_from_server(user, message[1], socket)


def rename_from_server(user, new_username, socket):
    """
    Renames the user informing the other users the old and current name of the user.
    If the old name is present in the other's friend's list, it will be changed to the new one.

    :param user: User object containing all his details (socket, username, state etc.)
    :param new_username: The new username.
    :param socket: Socket of the user.
    """
    try:
        old_username = user.username
        user.username = new_username
        global can_access_data
        with mutex_access_data:
            accessing_data_condition.wait_for(lambda: can_access_data)
            can_access_data = False
            for user in clients:
                if old_username in user.friends:
                    user.remove_friends(old_username)
                    user.add_friends(new_username)

                if old_username in user.pending_friends:
                    user.remove_pending_friends(old_username)
                    user.add_pending_friends(new_username)

        with mutex_access_data:
            can_access_data = True
            accessing_data_condition.notify_all()

        broadcast(f"renameFromSrv|{old_username}|{new_username}")
        unicast("200", socket)
    except s.error:
        unicast("500", socket)


def channel(socket, message):
    """
    Checks if userA is able to request a private channel with userB.
    UserA must:
        1. Enter the correct amount of parameters.
        2. Must be logged in.
        3. Not be in the 'afk' state.
        4. Enter a valid username attached to an online user.
        5. Not enter his own username.
        6. Not have already established a private channel userB.
        7. Not have already sent the same request to userB.

    In the event that one of these constraints are not met, userA will receive an error code and the function will stop.

    :param socket: Socket of userA.
    :param message: Message sent by userA containing:
                    1. The name of the command.
                    2. The username of userB.
    """

    # checks if command has the right number of parameters
    if len(message) != 2:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if not is_user_in_clients_list(user):
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    # checks if username exists
    if not is_username_connected(message[1]):
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
    """
    Sends a message informing userB of the private channel request from the userA.

    :param user: UserA object containing all his details (socket, username, state etc.)
    :param target_user: UserB object containing all his details (socket, username, state etc.)
    """
    try:
        target_user.add_pending_friends(user.username)
        unicast(f"channelFromSrv|{user.username}", target_user.socket)
        unicast("200", user.socket)
    except s.error:
        unicast("500", user.socket)


def acceptchannel(socket, message):
    """
    Checks if userA is able to accept the private channel request of userB.
    UserA must:
        1. Enter the correct amount of parameters.
        2. Must be logged in.
        3. Not be in the 'afk' state.
        4. Enter a valid username attached to an online user.
        5. Not enter his own username.
        6. Not have already established a private channel with userB.
        7. Have a private channel request.
        8. Enter the username of userB.

    In the event that one of these constraints are not met, userA will receive an error code and the function will stop.

    :param socket: Socket of userA.
    :param message: Message sent by userA containing:
                    1. The name of the command.
                    2. The username of userB.
    """
    # checks if command has the right number of parameters
    if len(message) != 2:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if not is_user_in_clients_list(user):
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    # checks if username exists
    if not is_username_connected(message[1]):
        unicast("402", socket)
        return

    targeted_user = find_user_by_username(message[1])

    # checks if the username given in the parameter isn't the client himself
    # alternatively we could check if user.username == message[1]
    if targeted_user.socket == socket:
        unicast("407", socket)
        return

    # checks if the username given in the parameter isn't already in the user's friends list
    if targeted_user.username in user.friends:
        unicast("404", socket)
        return

    # # checks if the user has any channel requests
    # if len(user.pending_friends) == 0:
    #     unicast("440", socket)
    #     return

    # checks if the username given in the parameter is in the user's pending friends request
    if targeted_user.username not in user.pending_friends:
        unicast("444", socket)
        return

    acceptchannel_from_server(user, targeted_user)


def acceptchannel_from_server(user, target_user):
    """
    Informs userB that userA accepted the private channel request.
    Once this, userB and userA can now private message each other.
    Deletes userB's username from userA's pending friends list and vice-versa.
    Adds userA's username to userB's friends list and vice-versa.

    :param user: UserA object containing all his details (socket, username, state etc.)
    :param target_user: UserB object containing all his details (socket, username, state etc.)
    """
    try:
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

        # checks if the target user is in the user's pending friends list
        # if he is, remove him from the list
        if target_user.username in user.pending_friends:
            user.remove_pending_friends(target_user.username)

        unicast(f"acceptedchannelFromSrv|{user.username}", target_user.socket)
        unicast("200", user.socket)
    except s.error:
        unicast("500", user.socket)


def declinechannel(socket, message):
    """
    Checks if userA is able to decline the private channel request of userB.
    UserA must:
        1. Enter the correct amount of parameters.
        2. Must be logged in.
        3. Not be in the 'afk' state.
        4. Enter a valid username attached to an online user.
        5. Not enter his own username.
        6. Not have already established a private channel with userB.
        7. Have a private channel request.
        8. Enter the username of userB.

    In the event that one of these constraints are not met, userA will receive an error code and the function will stop.

    :param socket: Socket of userA.
    :param message: Message sent by userA containing:
                    1. The name of the command.
                    2. The username of userB.
    """
    # checks if command has the right number of parameters
    if len(message) != 2:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if not is_user_in_clients_list(user):
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    # checks if username exists
    if not is_username_connected(message[1]):
        unicast("402", socket)
        return

    targeted_user = find_user_by_username(message[1])

    # checks if the username given in the parameter isn't the client himself
    # alternatively we could check if user.username == message[1]
    if targeted_user.socket == socket:
        unicast("407", socket)
        return

    # checks if the username given in the parameter isn't already in the user's friends list
    if targeted_user.username in user.friends:
        unicast("404", socket)
        return

    # # checks if the user has any channel requests
    # if len(user.pending_friends) == 0:
    #     unicast("440", socket)
    #     return

    # checks if the username given in the parameter is in the user's pending friends request
    if targeted_user.username not in user.pending_friends:
        unicast("444", socket)
        return

    declinechannel_from_server(user, targeted_user)


def declinechannel_from_server(user, target_user):
    """
    Informs userB that userA declined the private channel request.
    Deletes userB's username from userA's pending friends list and vice-versa.

    :param user: UserA object containing all his details (socket, username, state etc.)
    :param target_user: UserB object containing all his details (socket, username, state etc.)
    """
    try:
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
    except s.error:
        unicast("500", user.socket)


def msgpv(socket, message):
    """
    Checks if userA is able to send a private message to userB.
    UserA must:
        1. Enter the correct amount of parameters.
        2. Must be logged in.
        3. Not be in the 'afk' state.
        4. Enter a valid username attached to an online user.
        5. Not enter his own username.
        6. Have already established a private channel with userB.
        7. Enter the username of userB.

    In the event that one of these constraints are not met, userA will receive an error code and the function will stop.

    :param socket: Socket of userA.
    :param message: Message sent by userA containing:
                    1. The name of the command.
                    2. The username of userB.
                    3. The message to be sent to userB.
    """
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
    if not is_user_in_clients_list(user):
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    if mess == "":
        unicast("403", socket)
        return

    # checks if username exists
    # we create a new list of usernames and if the username given isn't in that list we send a code error
    if not is_username_connected(target_username):
        unicast("402", socket)
        return

    targeted_user = find_user_by_username(target_username)

    # checks if the username given in the parameter isn't the client himself
    # alternatively we could check if user.username == message[1]
    if targeted_user.socket == socket:
        unicast("407", socket)
        return

    # checks if the username given in the parameter is present in the user's friends list
    if target_username not in user.friends:
        unicast("421", socket)
        return

    msgpv_from_server(socket, user.username, targeted_user.socket, mess)


def msgpv_from_server(socket, username, target_socket, message):
    """
    userA sends a private message to userB.

    :param socket: Socket of userA.
    :param username: Username of userA.
    :param target_socket: Socket of userB.
    :param message: Message to be sent.
    """
    try:
        unicast(f"msgpvFromSrv|{username}|{message}", target_socket)
        unicast("200", socket)
    except s.error:
        unicast("500", socket)


def sharefile(socket, message):
    """
    Checks if userA is able to send a share file request to userB.
    UserA must:
        1. Enter the correct amount of parameters.
        2. Must be logged in.
        3. Not be in the 'afk' state.
        4. Enter a valid username attached to an online user.
        5. Not enter his own username.
        6. Not have already made the request to userB with the same file.
        7. Enter a valid path to file.
        8. Enter a valid port.

    In the event that one of these constraints are not met, userA will receive an error code and the function will stop.

    :param socket: Socket of userA.
    :param message: Message sent by userA containing:
                    1. The name of the command.
                    2. The username of userB.
                    3. The filepath.
                    4. The port to be used for transfer.
    """
    # checks if command has the right number of parameters
    if len(message) != 5:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if not is_user_in_clients_list(user):
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    # checks if username exists
    if not is_username_connected(message[1]):
        unicast("402", socket)
        return

    targeted_user = find_user_by_username(message[1])

    # checks if the username given in the parameter isn't the client himself
    # alternatively we could check if user.username == message[1]
    if targeted_user.socket == socket:
        unicast("407", socket)
        return

    file = message[2]
    # gets only the name and extension of the file
    if "\\" in message[2]:
        file = message[2].split("\\")
        file = file[-1]
    elif "/" in message[2]:
        file = message[2].split("/")
        file = file[-1]

    port = message[3]

    file_size = message[4]

    username_and_file = (user.username, file)

    # checks if the request with this specific file has already been made by the user to the user given in the parameter
    if username_and_file in targeted_user.pending_files:
        unicast("442", socket)
        return

    sharefile_from_server(user, file, targeted_user, port, file_size)


def sharefile_from_server(user, file, target_user, port, file_size):
    """
    userA sends a share file request to userB informing him of the file, its size, the address of userA and the port to be used for transfer.

    :param user: UserA object containing all his details (socket, username, state etc.).
    :param file: Name of the file to be sent.
    :param target_user: UserB object containing all his details (socket, username, state etc.).
    :param port: Port number to be used for transfer.
    :param file_size: Size of the file to be transferred.
    """
    try:
        target_user.add_pending_files((user.username, file))
        unicast(f"sharefileFromSrv|{user.username}|{file}|{file_size}|{user.socket.getsockname()[0]}|{port}",
                target_user.socket)
        unicast("200", user.socket)
    except s.error:
        unicast("500", user.socket)


def acceptfile(socket, message):
    """
    Checks if userA is able to accept a share file request from userB.
    UserA must:
        1. Enter the correct amount of parameters.
        2. Must be logged in.
        3. Not be in the 'afk' state.
        4. Enter a valid username attached to an online user.
        5. Not enter his own username.
        6. Have a share file request.
        7. Enter the name of the file given by userB.

    In the event that one of these constraints are not met, userA will receive an error code and the function will stop.

    :param socket: Socket of userA.
    :param message: Message sent by userA containing:
                    1. The name of the command.
                    2. The username of userB.
                    3. The name of the file given by userB.
    """
    # checks if command has the right number of parameters
    if len(message) != 3:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if not is_user_in_clients_list(user):
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    # checks if username exists
    if not is_username_connected(message[1]):
        unicast("402", socket)
        return

    # # checks if user has any pending files requests
    # if len(user.pending_files) == 0:
    #     unicast("445", socket)
    #     return

    targeted_user = find_user_by_username(message[1])

    # checks if the username given in the parameter isn't the client himself
    # alternatively we could check if user.username == message[1]
    if targeted_user.socket == socket:
        unicast("407", socket)
        return

    target_username_and_file = (message[1], message[2])

    # checks if the username given in the parameter is present in the user's pending files request list
    if message[1] not in user.pending_files[0]:
        unicast("443", socket)
        return

    # checks if the username and the file given in the parameters correspond with userB's share file request
    if target_username_and_file not in user.pending_files:
        unicast("406", socket)
        return

    acceptfile_from_server(socket, targeted_user.socket, user, target_username_and_file)


def acceptfile_from_server(socket, target_socket, user, target_username_and_file):
    """
    userA accepts the file share request from userB.
    Once this, userA will connect to userB with the provided data in order for the file to be transferred from userB to userA. (Done on the client side)
    Deletes the pending file request from userB from userA's pending file request list.

    :param socket: Socket of userA.
    :param target_socket: Socket of userB.
    :param user: UserA object containing all his details (socket, username, state etc.).
    :param target_username_and_file: Tuple containing the username and the name of the file of userB.
    """
    try:
        user.remove_pending_files(target_username_and_file)
        unicast(f"acceptedfileFromSrv|{user.username}|{target_username_and_file[1]}", target_socket)
        unicast("200", socket)
    except s.error:
        unicast("500", socket)


def declinefile(socket, message):
    """
    Checks if userA is able to decline a share file request from userB.
    UserA must:
        1. Enter the correct amount of parameters.
        2. Must be logged in.
        3. Not be in the 'afk' state.
        4. Enter a valid username attached to an online user.
        5. Not enter his own username.
        6. Have a share file request.
        7. Enter the name of the file given by userB.

    In the event that one of these constraints are not met, userA will receive an error code and the function will stop.

    :param socket: Socket of userA.
    :param message: Message sent by userA containing:
                    1. The name of the command.
                    2. The username of userB.
                    3. The name of the file given by userB.
    """
    # checks if command has the right number of parameters
    if len(message) != 3:
        unicast("403", socket)
        return

    user = find_user_by_socket(socket)

    # checks if user is connected
    if not is_user_in_clients_list(user):
        unicast("418", socket)
        return

    # checks if user's state is 'afk'
    if user.state == 'afk':
        unicast("430", socket)
        return

    # checks if username exists
    if not is_username_connected(message[1]):
        unicast("402", socket)
        return

    # if len(user.pending_files) == 0:
    #     unicast("445", socket)
    #     return

    targeted_user = find_user_by_username(message[1])

    target_username_and_file = (message[1], message[2])

    # checks if the username given in the parameter is present in the user's pending files request list
    if message[1] not in user.pending_files[0]:
        unicast("443", socket)
        return

    # checks if the username and the file given in the parameters correspond with userB's share file request
    if target_username_and_file not in user.pending_files:
        unicast("406", socket)
        return

    declinefile_from_server(user, targeted_user, message[2])


def declinefile_from_server(user, target_user, file):
    """
    userA declines the file share request from userB.
    Deletes the pending file request from userB from userA's pending file request list.

    :param user: UserA object containing all his details (socket, username, state etc.).
    :param target_user: UserB object containing all his details (socket, username, state etc.).
    :param file: Name of the file.
    """
    try:
        user.remove_pending_files((target_user.username, file))
        unicast(f"declinedfileFromSrv|{user.username}|{file}", target_user.socket)
        unicast("200", user.socket)
    except s.error:
        unicast("500", user.socket)


def help_command(socket, message):
    """
    Checks if userA is able to invoke the help command.
    UserA must:
        1. Enter the correct amount of parameters.

    In the event that this constraint is not met, userA will receive an error code and the function will stop.

    :param socket: Socket of userA.
    :param message: Message sent by userA containing:
                    1. The name of the command.
    """
    # checks if command has the right number of parameters
    if len(message) != 1:
        unicast("403", socket)
        return

    unicast("200", socket)
    unicast("helpFromSrv|signup USERNAME: Sign up and log in to login to the chatroom.\nmsg MESSAGE: Send a message in the "
            "chatroom.\nmsgpv USERNAME MESSAGE : Send a message to a specific user.\nexit: Leave the server.\nafk : "
            "Enter afk mode to prevent from sending messages. Note - In this mode, it is possible to only use the "
            "'exit' command.\nbtk: Return from afk mode and enter btk mode to send commands and messages once "
            "again.\nusers: View the list of connected users.\nrename USERNAME: Change your username.\nping "
            "USERNAME: Send a ping to a user.\nchannel USERNAME: Request a private channel with a specific "
            "user.\nacceptchannel USERNAME: Accept the private channel request.\ndeclinechannel USERNAME: Decline "
            "the private channel request.\nsharefile USERNAME FILE_NAME: Request a file to share with a specific "
            "user. \nacceptfile USERNAME FILE_NAME: Accept the file to share request.\ndeclinefile USERNAME "
            "FILE_NAME: Decline de file to share request.", socket)


def process_client(client_socket, client_address):
    """
    Processes the input command of each user.
    This function is threaded meaning each client will have his own thread.
    Also handles any abrupt disconnects from the clients.

    :param client_socket: Socket of the client.
    :param client_address: Address of the client.
    """
    write_to_log(f"{str(client_address)} HAS CONNECTED.")
    while True:
        try:
            message = client_socket.recv(SIZE).decode(FORMAT)
            if not len(message):
                return
            write_to_log(f"FROM {str(adr_client)} REQUEST: {message}")
            command = message.split(" ")
            if command[0] == "signup":
                signup(client_socket, command)
            elif command[0] == "help":
                help_command(client_socket, command)
            elif command[0] == "msg":
                msg(client_socket, command)
            elif command[0] == "exit":
                exit(client_socket, command)
                break
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
        except s.error:
            # finds the user by socket
            user = find_user_by_socket(client_socket)
            if user is not None:
                username = user.username
            # removes the user from the clients list
                remove_user(client_socket)
                broadcast(f"exitedFromSrv|{username}")
            write_to_log(f"SUDDEN DISCONNECT FROM {str(adr_client)}")
            client_socket.close()
            print(f"Client {str(client_address)} disconnected.")
            break


if __name__ == '__main__':
    if len(sys.argv) != 1:
        print(f"Usage: {sys.argv[0]}", file=sys.stderr)
        sys.exit(1)

    print("Server is now running.")
    clients = []

    read_from_config()

    sock_locale = s.socket(s.AF_INET, s.SOCK_STREAM)
    sock_locale.bind((SERVER_HOST, int(SERVER_PORT)))
    sock_locale.listen()
    write_to_log(f"Server has started. Listening on port '{SERVER_PORT}'".upper())
    while True:
        try:
            sock_client, adr_client = sock_locale.accept()
            print(f"Client {str(adr_client)} connected.")
            threading.Thread(target=process_client, args=(sock_client, adr_client, )).start()

        except KeyboardInterrupt:
            break
    print("Bye")

    for t in threading.enumerate():
        if t != threading.main_thread():
            t.join()

    sys.exit(0)
