import socket
import threading

HOST = '127.0.0.1'
PORT = 8888
SIZE = 1024
FORMAT = 'utf-8'


def receive_message(client_socket):
    while True:
        try:
            from_server = client_socket.recv(SIZE).decode(FORMAT)
            print(f"From Server: {from_server}")
            if from_server == "400":
                print("This command does not exist")
            if from_server == "401":
                print("Message error")
            if from_server == "402":
                print("Username given does not exist or is not logged in.")
            if from_server == "403":
                print("Wrong number of parameters.")
            if from_server == "404":
                print("Private channel already exists. You are already friends with that user.")
            if from_server == "405":
                print("File name given does not exist.")
            if from_server == "406":
                print("Username given does not exist or is not logged in.")
            if from_server == "407":
                print("You are not authorized to send that to yourself.")
            if from_server == "415":
                print("You are already away from keyboard")
            if from_server == "416":
                print("You are already chatting/back to keyboard")
            if from_server == "417":
                print("You are already logged in")
            if from_server == "418":
                print("You must be logged in to input this command.")
            if from_server == "425":
                print("Username is already taken, choose another")
            if from_server == "426":
                print("Username must not contain any special characters or numbers")
            if from_server == "430":
                print("You are away from keyboard.")
            if from_server == "500":
                print("Internal server error")

            if from_server.startswith("signup"):
                message = from_server.split("|")
                print(f"{message[1]} has joined the chatroom!")
            if from_server.startswith("msg"):
                message = from_server.split("|")
                print(f"{message[1]} : {message[2]}")
            if from_server.startswith("exit"):
                message = from_server.split("|")
                print(f"{message[1]} has left the chatroom.")
            if from_server.startswith("afk"):
                message = from_server.split("|")
                print(f"{message[1]} is now away from keyboard.")
            if from_server.startswith("btk"):
                message = from_server.split("|")
                print(f"{message[1]} is now back to keyboard.")
            if from_server.startswith("users"):
                message = from_server.split("|")
                print(f"List of connected users : {message[1]}")
            if from_server.startswith("rename"):
                message = from_server.split("|")
                print(f"{message[1]} changed his name to {message[2]}.")
            if from_server.startswith("ping"):
                message = from_server.split("|")
                print(f"{message[1]} has pinged you!")
            if from_server.startswith("channel"):
                message = from_server.split("|")
                print(f"{message[1]} requests a private channel with you. Do you accept?")
            if from_server.startswith("acceptchannel"):
                message = from_server.split("|")
                print(f"{message[1]} has accepted your request. You can now DM {message[1]}")
            if from_server.startswith("declinechannel"):
                message = from_server.split("|")
                print(f"{message[1]} has declined your request.")
            if from_server.startswith("sharefile"):
                message = from_server.split("|")
                print(f"{message[2]} requests to share the file {message[3]} with you. Do you accept?")
            if from_server.startswith("acceptsharefile"):
                message = from_server.split("|")
                print(f"{message[1]} accepted your transfer for file {message[2]}. Transferring...")
            if from_server.startswith("declinesharefile"):
                message = from_server.split("|")
                print(f"{message[1]} declined your transfer for file {message[2]}.")
            if from_server.startswith("exitFromSrv"):
                client_socket.close()

        except ConnectionResetError:
            print("\nDisconnected from server.")
            break


def send_message(client_socket):
    while True:
        try:
            message = input()
            client_socket.sendall(message.encode(FORMAT))
        except ConnectionResetError:
            print("\nDisconnected from server.")
            break


if __name__ == '__main__':
    socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket.connect((HOST, PORT))

    print("Connected to the server! Type 'signup <username>' to join the chatroom.")

    threading.Thread(target=receive_message, args=(socket, )).start()
    threading.Thread(target=send_message, args=(socket, )).start()

