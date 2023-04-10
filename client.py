import socket as s
import yaml
import threading

SERVER_HOST = ''
SERVER_PORT = 0
BUFFER_SIZE = 1024
FORMAT = 'utf-8'
stop_thread = False
INPUT_COMMAND = ''
DOWNLOADS_PATH = ''
global SENDER_HOST
global COMMON_PORT
pending_files = {}
is_transfer_complete = False
can_say_transfer_complete = True
transfer_mutex = threading.Lock()
can_say_transfer_condition = threading.Condition(transfer_mutex)
FILE_PATH = ''
global socket


def send_file(path, sender_host, port):
    server_socket = s.socket(s.AF_INET, s.SOCK_STREAM)
    server_socket.bind((sender_host, int(port)))
    server_socket.listen(1)

    client_socket, client_address = server_socket.accept()

    with open(path, 'rb') as file:
        data = file.read(1024)
        while data:
            client_socket.send(data)
            data = file.read(1024)

    with transfer_mutex:
        global can_say_transfer_complete
        can_say_transfer_condition.wait_for(lambda: can_say_transfer_complete)
        can_say_transfer_complete = False
        global is_transfer_complete
        is_transfer_complete = True

    with transfer_mutex:
        can_say_transfer_complete = True
        can_say_transfer_condition.notify_all()

    client_socket.close()
    server_socket.close()


def receive_file(filename, port, sender_host):
    client_socket = s.socket(s.AF_INET, s.SOCK_STREAM)
    client_socket.connect((sender_host, int(port)))

    filepath = DOWNLOADS_PATH + filename

    with open(filepath, 'wb') as file:
        data = client_socket.recv(1024)
        while data:
            file.write(data)
            data = client_socket.recv(1024)

    with transfer_mutex:
        global can_say_transfer_complete
        can_say_transfer_condition.wait_for(lambda: can_say_transfer_complete)
        can_say_transfer_complete = False
        global is_transfer_complete
        is_transfer_complete = True

    with transfer_mutex:
        can_say_transfer_complete = True
        can_say_transfer_condition.notify_all()

    client_socket.close()


def read_from_config():
    with open('adinat_config.yaml', 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.FullLoader)

    global SERVER_HOST
    SERVER_HOST = config['client']['host']
    global SERVER_PORT
    SERVER_PORT = config['client']['port']
    global DOWNLOADS_PATH
    DOWNLOADS_PATH = config['client']['downloads']


def return_error_message(error_code):
    res = None
    if error_code == "400":
        res = f"The command '{INPUT_COMMAND[0]}' does not exist."
    if error_code == "401":
        res = "Message error."
    if error_code == "402":
        res = f"Username '{INPUT_COMMAND[1]}' does not exist or is not logged in."
    if error_code == "403":
        res = "Wrong number of parameters."
    if error_code == "404":
        res = f"Private channel with user '{INPUT_COMMAND[1]}' already exists."
    if error_code == "405":
        res = f"File '{INPUT_COMMAND[2]}' does not exist."
    if error_code == "406":
        res = f"The file name '{INPUT_COMMAND[2]}' isn't corresponding with the file name given by user '{INPUT_COMMAND[1]}'."
    if error_code == "407":
        res = f"You are not authorized to issue the command '{INPUT_COMMAND[0]}' to yourself."
    if error_code == "415":
        res = "You are already away from keyboard."
    if error_code == "416":
        res = "You are already chatting/back to keyboard."
    if error_code == "417":
        res = "You are already logged in."
    if error_code == "418":
        res = f"You must be logged in to input the command '{INPUT_COMMAND[0]}'."
    if error_code == "421":
        res = f"You must first issue a private channel request from '{INPUT_COMMAND[1]}' in order to private message him."
    if error_code == "425":
        res = f"Username '{INPUT_COMMAND[1]}' is already taken by another user. Input the command 'signup USERNAME' once again with another username. "
    if error_code == "426":
        res = "Username must not contain any special characters or numbers."
    if error_code == "430":
        res = "You are away from keyboard."
    if error_code == "440":
        res = "You don't have any pending private channel requests."
    if error_code == "441":
        res = f"You already issued a private channel request to {INPUT_COMMAND[1]}."
    if error_code == "442":
        res = f"You have already issued a file transfer request with the file '{INPUT_COMMAND[2]}' to {INPUT_COMMAND[1]}."
    if error_code == "443":
        res = f"You don't have any pending file share requests."
    if error_code == "444":
        res = f"You have no pending private channel request from {INPUT_COMMAND[1]}."
    if error_code == "445":
        res = f"You have no pending share file request from {INPUT_COMMAND[1]}."
    if error_code == "446":
        res = f"Port number '{INPUT_COMMAND[1]}' is not valid."
    if error_code == "500":
        res = "Internal server error."
    return res


def return_passing_messages():
    res = None
    if INPUT_COMMAND[0] == "channel":
        res = f"You sent a private channel request to {INPUT_COMMAND[1]}."
    if INPUT_COMMAND[0] == "declinechannel":
        res = f"You declined {INPUT_COMMAND[1]}'s  private channel request."
    if INPUT_COMMAND[0] == "sharefile":
        res = f"You sent a share file request to {INPUT_COMMAND[1]}."
        global FILE_PATH, COMMON_PORT, SENDER_HOST
        FILE_PATH = INPUT_COMMAND[2]
        COMMON_PORT = INPUT_COMMAND[3]
        SENDER_HOST = socket.getsockname()[0]
    if INPUT_COMMAND[0] == "acceptchannel":
        res = f"You accepted {INPUT_COMMAND[1]}'s  private channel request. You can now DM {INPUT_COMMAND[1]}."
    if INPUT_COMMAND[0] == "declinefile":
        res = f"You declined {INPUT_COMMAND[1]}'s share file request for the file '{INPUT_COMMAND[2]}'"
        del pending_files[(INPUT_COMMAND[1], INPUT_COMMAND[2])]
    if INPUT_COMMAND[0] == "acceptfile":
        res = f"You accepted {INPUT_COMMAND[1]}'s share file request for the file '{INPUT_COMMAND[2]}'"
        port = pending_files[(INPUT_COMMAND[1], INPUT_COMMAND[2])]['COMMON_PORT']
        host = pending_files[(INPUT_COMMAND[1], INPUT_COMMAND[2])]['SENDER_HOST']
        receive_file_thread = threading.Thread(target=receive_file, args=(INPUT_COMMAND[2], port, host, ))
        receive_file_thread.start()
        receive_file_thread.join()
    if INPUT_COMMAND[0] == "ping":
        res = f"You successfully pinged {INPUT_COMMAND[1]}."
    if INPUT_COMMAND[0] == "rename":
        res = f"You successfully changed your name to {INPUT_COMMAND[1]}."
    if INPUT_COMMAND[0] == "help":
        res = "signup USERNAME: Sign up and log in to login to the chatroom.\nmsg MESSAGE: Send a message in the " \
              "chatroom.\nmsgpv USERNAME MESSAGE : Send a message to a specific user.\nexit: Leave the server.\nafk : " \
              "Enter afk mode to prevent from sending messages. Note - In this mode, it is possible to only use the " \
              "'exit' command.\nbtk: Return from afk mode and enter btk mode to send commands and messages once " \
              "again.\nusers: View the list of connected users.\nrename USERNAME: Change your username.\nping " \
              "USERNAME: Send a ping to a user.\nchannel USERNAME: Request a private channel with a specific " \
              "user.\nacceptchannel USERNAME: Accept the private channel request.\ndeclinechannel USERNAME: Decline " \
              "the private channel request.\nsharefile USERNAME FILE_NAME: Request a file to share with a specific " \
              "user. \nacceptfile USERNAME FILE_NAME: Accept the file to share request.\ndeclinefile USERNAME " \
              "FILE_NAME: Decline de file to share request. "
    return res


def return_messages_with_data(message):
    res = None
    message = message.split("|")
    if message[0].startswith("signup"):
        res = f"{message[1]} has joined the chatroom!"
    if message[0].startswith("msg"):
        res = f"{message[1]}: {message[2]}"
    if message[0].startswith("msgpv"):
        res = f"DM from {message[1]}: {message[2]}"
    if message[0].startswith("exited"):
        res = f"{message[1]} has left the server."
    if message[0].startswith("afk"):
        res = f"{message[1]} is now away from keyboard."
    if message[0].startswith("btk"):
        res = f"{message[1]} is now back to keyboard."
    if message[0].startswith("users"):
        res = f"List of connected users : {message[1]}"
    if message[0].startswith("rename"):
        res = f"{message[1]} changed his name to {message[2]}."
    if message[0].startswith("ping"):
        res = f"{message[1]} has pinged you!"
    if message[0].startswith("channel"):
        res = f"{message[1]} requests a private channel with you. Do you accept?"
    if message[0].startswith("acceptedchannel"):
        res = f"{message[1]} has accepted your private channel request. You can now DM {message[1]}"
    if message[0].startswith("declinedchannel"):
        res = f"{message[1]} has declined your private channel request."
    if message[0].startswith("sharefile"):
        res = f"{message[1]} requests to share the file '{message[2]}' [{message[3]}] with you on port {message[5]}. Do you accept? "
        global pending_files
        pending_files[(message[1], message[2])] = {'SENDER_HOST': message[4], 'COMMON_PORT': message[5]}
    if message[0].startswith("acceptedfile"):
        res = f"{message[1]} accepted your transfer for file {message[2]}. Transferring..."
        send_file_thread = threading.Thread(target=send_file, args=(FILE_PATH, SENDER_HOST, COMMON_PORT,))
        send_file_thread.start()
        send_file_thread.join()
    if message[0].startswith("declinedfile"):
        res = f"{message[1]} declined your transfer for file '{message[2]}'."
    return res


def receive_message(client_socket):
    while True:
        if stop_thread:
            break
        try:
            from_server = client_socket.recv(BUFFER_SIZE).decode(FORMAT)
            print(f"From Server: {from_server}")
            global INPUT_COMMAND, is_transfer_complete
            if not isinstance(INPUT_COMMAND, list):
                INPUT_COMMAND = INPUT_COMMAND.split()

            if from_server != "200":
                error_message = return_error_message(from_server)
                if error_message is not None:
                    print(error_message)

            if from_server == "200":
                passing_messages = return_passing_messages()
                if passing_messages is not None:
                    print(passing_messages)

            data_messages = return_messages_with_data(from_server)
            if data_messages is not None:
                print(data_messages)

            if is_transfer_complete:
                print("Transfer complete")
                is_transfer_complete = False

        except ConnectionResetError or ConnectionAbortedError:
            print("\nDisconnected from the server.")
            client_socket.close()
            break


def send_message(client_socket):
    global INPUT_COMMAND
    global stop_thread
    while True:
        if stop_thread:
            break
        try:
            INPUT_COMMAND = input()
            if INPUT_COMMAND.lower() == "exit":
                stop_thread = True
            client_socket.sendall(INPUT_COMMAND.lower().encode(FORMAT))
        except ConnectionResetError or ConnectionAbortedError:
            print("\nDisconnected from the server.")
            break


if __name__ == '__main__':
    try:
        read_from_config()

        socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        print(SERVER_HOST)
        print(SERVER_PORT)
        socket.connect((SERVER_HOST, int(SERVER_PORT)))

        print("Connected to the server! Type 'signup <username>' to join the chatroom.")

        threading.Thread(target=receive_message, args=(socket,)).start()
        threading.Thread(target=send_message, args=(socket,)).start()
    except KeyboardInterrupt:
        print("Closing...")

