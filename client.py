import socket
import yaml
import threading

HOST = ''
PORT = 0
SIZE = 1024
FORMAT = 'utf-8'
stop_thread = False
COMMAND = ''
TARGET_HOST = ''
TARGET_PORT = 0
DOWNLOADS = ''


def get_target_port(port):
    global TARGET_PORT
    TARGET_PORT = int(port)


def read_from_config():
    with open('adinat_config.yaml', 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.FullLoader)

    global HOST
    HOST = config['client']['host']
    global PORT
    PORT = config['client']['port']
    global DOWNLOADS
    DOWNLOADS = config['client']['downloads']


def return_error_message(error_code):
    res = None
    if error_code == "400":
        res = f"The command '{COMMAND[0]}' does not exist."
    if error_code == "401":
        res = "Message error."
    if error_code == "402":
        res = f"Username '{COMMAND[1]}' does not exist or is not logged in."
    if error_code == "403":
        res = "Wrong number of parameters."
    if error_code == "404":
        res = f"Private channel with user '{COMMAND[1]}' already exists."
    if error_code == "405":
        res = f"File '{COMMAND[2]}' does not exist."
    if error_code == "406":
        res = f"The file name {COMMAND[2]} isn't corresponding with the file name given by user '{COMMAND[1]}'."
    if error_code == "407":
        res = f"You are not authorized to issue the command '{COMMAND[0]}' to yourself."
    if error_code == "415":
        res = "You are already away from keyboard."
    if error_code == "416":
        res = "You are already chatting/back to keyboard."
    if error_code == "417":
        res = "You are already logged in."
    if error_code == "418":
        res = f"You must be logged in to input the command '{COMMAND[0]}'."
    if error_code == "421":
        res = f"You must first issue a private channel request from user '{COMMAND[1]}' in order to private message him."
    if error_code == "425":
        res = f"Username '{COMMAND[1]}' is already taken by another user. Input the command 'signup USERNAME' once " \
              f"again with another username. "
    if error_code == "426":
        res = "Username must not contain any special characters or numbers."
    if error_code == "430":
        res = "You are away from keyboard."
    if error_code == "440":
        res = "You don't have any pending private channel requests."
    if error_code == "441":
        res = f"You already issued a private channel request to user '{COMMAND[1]}'."
    if error_code == "442":
        res = f"You have already issued a file transfer request with the file '{COMMAND[2]}' to user '{COMMAND[1]}'"
    if error_code == "500":
        res = "Internal server error."
    return res


def return_passing_messages():
    res = None
    if COMMAND[0] == "channel":
        res = f"You sent a private channel request to {COMMAND[1]}."
    if COMMAND[0] == "declinechannel":
        res = f"You declined {COMMAND[1]}'s  private channel request."
    if COMMAND[0] == "sharefile":
        res = f"You sent a share file request to {COMMAND[1]}."
        get_target_port(COMMAND[3])
    if COMMAND[0] == "acceptchannel":
        res = f"You accepted {COMMAND[1]}'s  private channel request. You can now DM {COMMAND[1]}."
    if COMMAND[0] == "declinefile":
        res = f"You declined {COMMAND[1]}'s share file request for the file '{COMMAND[2]}'"
    if COMMAND[0] == "acceptfile":
        res = f"You accepted {COMMAND[1]}'s share file request for the file '{COMMAND[2]}'"
    if COMMAND[0] == "ping":
        print(f"You successfully pinged {COMMAND[1]}.")
        res = f"You successfully pinged {COMMAND[1]}."
    if COMMAND[0] == "rename":
        res = f"You successfully changed your name to {COMMAND[1]}."
    if COMMAND[0] == "help":
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
    if message[0].startswith("exit"):
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
        res = f"{message[1]} requests to share the file '{message[2]}' [{message[3]}] with you on port {message[4]}. Do you accept?"
        get_target_port(message[4])
    if message[0].startswith("acceptedfile"):
        res = f"{message[1]} accepted your transfer for file {message[2]}. Transferring..."
    if message[0].startswith("declinedfile"):
        res = f"{message[1]} declined your transfer for file {message[2]}."
    return res


def receive_message(client_socket):
    while True:
        if stop_thread:
            break
        try:
            from_server = client_socket.recv(SIZE).decode(FORMAT)
            print(f"From Server: {from_server}")
            global COMMAND
            if not isinstance(COMMAND, list):
                COMMAND = COMMAND.split()

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

        except ConnectionResetError or ConnectionAbortedError:
            print("\nDisconnected from the server.")
            client_socket.close()
            break


def send_message(client_socket):
    global COMMAND
    global stop_thread
    while True:
        if stop_thread:
            break
        try:
            COMMAND = input().lower()
            if COMMAND == "exit":
                stop_thread = True
            client_socket.sendall(COMMAND.encode(FORMAT))
        except ConnectionResetError or ConnectionAbortedError:
            print("\nDisconnected from the server.")
            break


if __name__ == '__main__':
    try:
        read_from_config()

        socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket.connect((HOST, int(PORT)))

        print("Connected to the server! Type 'signup <username>' to join the chatroom.")

        threading.Thread(target=receive_message, args=(socket, )).start()
        threading.Thread(target=send_message, args=(socket, )).start()
    except KeyboardInterrupt:
        print("Closing...")

