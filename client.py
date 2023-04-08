import socket
import yaml
import threading

HOST = ''
PORT = 0
SIZE = 1024
FORMAT = 'utf-8'
stop_thread = False
COMMAND = ''


def read_from_config():
    with open('adinat_config.yaml', 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.FullLoader)

    global HOST
    HOST = config['client']['host']
    global PORT
    PORT = config['client']['port']


def return_error_message(error_code):
    if error_code == "400":
        print(f"The command '{COMMAND[0]}' does not exist.")
    if error_code == "401":
        print("Message error.")
    if error_code == "402":
        print(f"Username '{COMMAND[1]}' does not exist or is not logged in.")
    if error_code == "403":
        print("Wrong number of parameters.")
    if error_code == "404":
        print(f"Private channel with user '{COMMAND[1]}' already exists.")
    if error_code == "405":
        print(f"File '{COMMAND[2]}' does not exist.")
    if error_code == "407":
        print(f"You are not authorized to issue the command '{COMMAND[0]}' to yourself.")
    if error_code == "415":
        print("You are already away from keyboard.")
    if error_code == "416":
        print("You are already chatting/back to keyboard.")
    if error_code == "417":
        print("You are already logged in.")
    if error_code == "418":
        print(f"You must be logged in to input the command '{COMMAND[0]}'.")
    if error_code == "421":
        print(f"You must first issue a private channel request from user '{COMMAND[1]}' in order to private message him.")
    if error_code == "425":
        print(f"Username '{COMMAND[1]}' is already taken by another user. Input the command 'signup USERNAME' once "
              f"again with another username.")
    if error_code == "426":
        print("Username must not contain any special characters or numbers.")
    if error_code == "430":
        print("You are away from keyboard.")
    if error_code == "440":
        print("You don't have any pending private channel requests.")
    if error_code == "441":
        print(f"You already issued a private channel request to user '{COMMAND[1]}'.")
    if error_code == "500":
        print("Internal server error.")


def return_passing_messages():
    if COMMAND[0] == "channel":
        print(f"You sent a private channel request to {COMMAND[1]}.")
    if COMMAND[0] == "declinechannel":
        print(f"You declined {COMMAND[1]}'s  private channel request.")
    if COMMAND[0] == "sharefile":
        print(f"You sent a share file request to {COMMAND[1]}.")
    if COMMAND[0] == "acceptchannel":
        print(f"You accepted {COMMAND[1]}'s  private channel request. You can now DM {COMMAND[1]}.")
    if COMMAND[0] == "help":
        print('signup USERNAME: Sign up and log in to login to the chatroom.\nmsg MESSAGE: Send a '
              'message in the chatroom.\nmsgpv USERNAME MESSAGE : Send a message to a specific user.'
              '\nexit: Leave the server.\nafk : Enter afk mode to prevent from sending messages. Note - In this '
              'mode, it is possible to only use the "exit" command. '
              '\nbtk: Return from afk mode and enter btk mode to send commands and messages once again.\nusers : '
              'View the list of connected users.\nrename USERNAME : Change your username.'
              '\nping USERNAME: Send a ping to a user.\nchannel USERNAME: '
              'Request a private channel with a specific user.\nacceptchannel '
              'USERNAME: Accept the private channel request.\ndeclinechannel USERNAME: Decline '
              'the private channel request.\nsharefile USERNAME FILE_NAME: Request a file to share with a specific '
              'user. '
              '\nacceptfile USERNAME FILE_NAME: Accept the file to share request.\ndeclinefile USERNAME FILE_NAME: '
              'Decline de file to share request.')


def return_messages_with_data(message):
    message = message.split("|")
    if message[0].startswith("signup"):
        print(f"{message[1]} has joined the chatroom!")
    if message[0].startswith("msg"):
        print(f"{message[1]}: {message[2]}")
    if message[0].startswith("msgpv"):
        print(f"DM from {message[1]}: {message[2]}")
    if message[0].startswith("exit"):
        print(f"{message[1]} has left the server.")
    if message[0].startswith("afk"):
        print(f"{message[1]} is now away from keyboard.")
    if message[0].startswith("btk"):
        print(f"{message[1]} is now back to keyboard.")
    if message[0].startswith("users"):
        print(f"List of connected users : {message[1]}")
    if message[0].startswith("rename"):
        print(f"{message[1]} changed his name to {message[2]}.")
    if message[0].startswith("ping"):
        print(f"{message[1]} has pinged you!")
    if message[0].startswith("channel"):
        print(f"{message[1]} requests a private channel with you. Do you accept?")
    if message[0].startswith("acceptedchannel"):
        print(f"{message[1]} has accepted your private channel request. You can now DM {message[1]}")
    if message[0].startswith("declinedchannel"):
        print(f"{message[1]} has declined your private channel request.")
    if message[0].startswith("sharefile"):
        print(f"{message[2]} requests to share the file {message[3]} with you. Do you accept?")
    if message[0].startswith("acceptedsharefile"):
        print(f"{message[1]} accepted your transfer for file {message[2]}. Transferring...")
    if message[0].startswith("declinedsharefile"):
        print(f"{message[1]} declined your transfer for file {message[2]}.")


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
                return_error_message(from_server)

            if from_server == "200":
                return_passing_messages()

            return_messages_with_data(from_server)

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

