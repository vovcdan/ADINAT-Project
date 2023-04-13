import os
import socket as s
import yaml
import threading
import tkinter as tk
from tkinter import scrolledtext
import tkinter.ttk as ttk

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
global window
global input_field
global output

# Configuration des couleurs pour le thème Equilux
COLOR_BACKGROUND = "#23272a"
COLOR_TEXT = "white"

COLOR_ERROR = "red"
COLOR_NORMAL = "white"
COLOR_INFO = "#7289da"
COLOR_PV = "#99aab5"


def create_interface():
    global window
    # Créer la fenêtre principale de l'interface graphique
    window = tk.Tk()

    window.title("ADINAT Chatroom Client")
    window.configure(bg=COLOR_BACKGROUND)

    def on_closing():
        global stop_thread
        stop_thread = True
        socket.close()
        window.destroy()

    def send_on_enter(event):
        send_message(socket, input_field.get())
        input_field.delete(0, tk.END)

    window.protocol("WM_DELETE_WINDOW", on_closing)

    # Créer un champ de saisie pour la commande
    global input_field
    input_field = tk.Entry(window, width=40, bg=COLOR_BACKGROUND, fg=COLOR_TEXT, insertbackground=COLOR_TEXT, font=("Helvetica", 12))
    input_field.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W+tk.E)
    input_field.focus_set()

    # Créer une fenêtre de texte pour afficher la sortie de la commande
    global output
    output = scrolledtext.ScrolledText(window, width=80, height=20, wrap = tk.WORD,bg=COLOR_BACKGROUND, fg=COLOR_TEXT, insertbackground=COLOR_TEXT, font=("Helvetica", 12))
    output.grid(row=0, column=0, padx=5, pady=5, columnspan=2, sticky=tk.W+tk.E+tk.N+tk.S)
    output.see(tk.END)

    # Créer un bouton pour exécuter la commande
    button = tk.Button(window, text="Send", command=lambda: send_message(socket, input_field.get()), width=10, bg=COLOR_BACKGROUND, fg=COLOR_TEXT, font=("Helvetica", 12))
    button.grid(row=1, column=1, padx=5, pady=5, sticky="E")

    window.bind('<Return>', send_on_enter)
    window.grid_rowconfigure(0, weight=1)
    window.grid_columnconfigure(0, weight=1)

    # Lancer la boucle d'événements de l'interface graphique
    show_text("Connected to the server! Type 'signup <username>' to join the chatroom.", "normal")
    window.mainloop()

def show_text(text, couleur):
    if window.winfo_exists():
        if couleur == "error":
            output.insert(tk.END, text + '\n', 'error')
        elif couleur == "info":
            output.insert(tk.END, text + '\n', 'info')
        elif couleur == "pv":
            output.insert(tk.END, text + '\n', 'pv')
        else:
            output.insert(tk.END, text + '\n', 'normal')

    output.tag_config('error', foreground=COLOR_ERROR)
    output.tag_config('info', foreground=COLOR_INFO)
    output.tag_config('pv', foreground=COLOR_PV)
    output.tag_config('normal',  foreground=COLOR_TEXT)
    output.see(tk.END) #defilement vers le bas


def convert_bytes(size):
    """
    Convert bytes to KB, or MB or GB.

    :param size: Size of the bytes.
    :return double
    """
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return "%3.1f%s" % (size, x)
        size /= 1024.0


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
        res = (f"You sent a private channel request to {INPUT_COMMAND[1]}.","info")
    if INPUT_COMMAND[0] == "declinechannel":
        res = (f"You declined {INPUT_COMMAND[1]}'s  private channel request.","pv")
    if INPUT_COMMAND[0] == "msgpv":
        mess = ' '.join(INPUT_COMMAND[2:])
        res = (f"DM to {INPUT_COMMAND[1]}: {mess}","pv")
    if INPUT_COMMAND[0] == "sharefile":
        res = (f"You sent a share file request to {INPUT_COMMAND[1]}.","pv")
        global FILE_PATH, COMMON_PORT, SENDER_HOST
        FILE_PATH = INPUT_COMMAND[2]
        COMMON_PORT = INPUT_COMMAND[3]
        SENDER_HOST = socket.getsockname()[0]
    if INPUT_COMMAND[0] == "acceptchannel":
        res = (f"You accepted {INPUT_COMMAND[1]}'s  private channel request. You can now DM {INPUT_COMMAND[1]}.","pv")
    if INPUT_COMMAND[0] == "declinefile":
        res = (f"You declined {INPUT_COMMAND[1]}'s share file request for the file '{INPUT_COMMAND[2]}'","pv")
        del pending_files[(INPUT_COMMAND[1], INPUT_COMMAND[2])]
    if INPUT_COMMAND[0] == "acceptfile":
        res = (f"You accepted {INPUT_COMMAND[1]}'s share file request for the file '{INPUT_COMMAND[2]}'","pv")
        port = pending_files[(INPUT_COMMAND[1], INPUT_COMMAND[2])]['COMMON_PORT']
        host = pending_files[(INPUT_COMMAND[1], INPUT_COMMAND[2])]['SENDER_HOST']
        receive_file_thread = threading.Thread(target=receive_file, args=(INPUT_COMMAND[2], port, host, ))
        receive_file_thread.start()
        receive_file_thread.join()
    if INPUT_COMMAND[0] == "ping":
        res = (f"You successfully pinged {INPUT_COMMAND[1]}.","info")
    if INPUT_COMMAND[0] == "rename":
        res = (f"You successfully changed your name to {INPUT_COMMAND[1]}.","info")
    return res


def return_messages_with_data(message):
    res = None
    message = message.split("|")
    if message[0].startswith("signup"):
        res = (f"{message[1]} has joined the chatroom!","info")
    if message[0].startswith("msgFrom"):
        res = (f"{message[1]}: {message[2]}","normal")
    if message[0].startswith("msgpv"):
        res = (f"DM from {message[1]}: {message[2]}", "pv")
    if message[0].startswith("exited"):
        res = (f"{message[1]} has left the server.","info")
    if message[0].startswith("afk"):
        res = (f"{message[1]} is now away from keyboard.","info")
    if message[0].startswith("btk"):
        res = (f"{message[1]} is now back to keyboard.","info")
    if message[0].startswith("users"):
        res = (f"List of connected users : {message[1]}","info")
    if message[0].startswith("rename"):
        res = (f"{message[1]} changed his name to {message[2]}.", "info")
    if message[0].startswith("ping"):
        res = (f"{message[1]} has pinged you!", "info")
    if message[0].startswith("channel"):
        res = (f"{message[1]} requests a private channel with you. Do you accept?","pv")
    if message[0].startswith("acceptedchannel"):
        res = (f"{message[1]} has accepted your private channel request. You can now DM {message[1]}","pv")
    if message[0].startswith("declinedchannel"):
        res = (f"{message[1]} has declined your private channel request.","pv")
    if message[0].startswith("sharefile"):
        res = (f"{message[1]} requests to share the file '{message[2]}' [{message[3]}] with you on port {message[5]}. Do you accept?","pv")
        global pending_files
        pending_files[(message[1], message[2])] = {'SENDER_HOST': message[4], 'COMMON_PORT': message[5]}
    if message[0].startswith("acceptedfile"):
        res = (f"{message[1]} accepted your transfer for file {message[2]}. Transferring...", "pv")
        send_file_thread = threading.Thread(target=send_file, args=(FILE_PATH, SENDER_HOST, COMMON_PORT,))
        send_file_thread.start()
        send_file_thread.join()
    if message[0].startswith("declinedfile"):
        res = (f"{message[1]} declined your transfer for file '{message[2]}'.","pv")
    if message[0].startswith("helpFromSrv"):
        res = (f"{message[1]}", "info")
    return res


def receive_message(client_socket):
    global stop_thread
    while not stop_thread:
        try:
            from_server = client_socket.recv(BUFFER_SIZE).decode(FORMAT)
            print(f"From Server: {from_server}")
            global INPUT_COMMAND, is_transfer_complete
            if not isinstance(INPUT_COMMAND, list):
                INPUT_COMMAND = INPUT_COMMAND.split()

            if from_server != "200":
                error_message = return_error_message(from_server)
                if error_message is not None:
                    show_text(error_message, "error")

            if from_server == "200":
                passing_messages = return_passing_messages()
                if passing_messages is not None:
                    show_text(passing_messages[0], passing_messages[1])

            data_messages = return_messages_with_data(from_server)
            if data_messages is not None:
                show_text(data_messages[0], data_messages[1])

            if is_transfer_complete:
                show_text("Transfer complete", "info")
                is_transfer_complete = False

        except ConnectionResetError or ConnectionAbortedError:
            show_text("\nDisconnected from the server.", "info")
            stop_thread = True
            # client_socket.close()
            break


def send_message(client_socket, command):
    global INPUT_COMMAND
    global stop_thread
    try:
        INPUT_COMMAND = command
        if not isinstance(INPUT_COMMAND, list):
            INPUT_COMMAND = INPUT_COMMAND.split()
        INPUT_COMMAND[0] = INPUT_COMMAND[0].lower()
        INPUT_COMMAND = ' '.join(INPUT_COMMAND)
        if INPUT_COMMAND == "exit":
            window.destroy()
            stop_thread = True
        if INPUT_COMMAND.startswith("sharefile"):
            if not isinstance(INPUT_COMMAND, list):
                INPUT_COMMAND = INPUT_COMMAND.split()

            if len(INPUT_COMMAND) != 4:
                show_text("Wrong number of parameters.", "error")
                return

            if not os.path.isfile(INPUT_COMMAND[2]):
                show_text(f"File '{INPUT_COMMAND[2]}' does not exist.", "error")
                return

            port = INPUT_COMMAND[3]
            # checks if port is within reach
            if int(port) > 65535:
                show_text(f"Port number '{INPUT_COMMAND[3]}' is not valid.", "error")
                return

            file = INPUT_COMMAND[2]
            # gets size of file
            file_size = os.path.getsize(file)
            # converts size of file to human-readable units, a.k.a. KB, MB or GB
            file_size = convert_bytes(file_size)

            INPUT_COMMAND.append(file_size)
            INPUT_COMMAND = ' '.join(INPUT_COMMAND)

        client_socket.sendall(INPUT_COMMAND.encode(FORMAT))
        input_field.delete(0, tk.END)
    except ConnectionResetError or ConnectionAbortedError:
        stop_thread = True
        show_text("\nDisconnected from the server.", "error")


if __name__ == '__main__':
    try:
        read_from_config()

        socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        socket.connect((SERVER_HOST, int(SERVER_PORT)))

        threading.Thread(target=create_interface).start()
        threading.Thread(target=receive_message, args=(socket,)).start()
    except KeyboardInterrupt:
        show_text("Closing...", "info")
