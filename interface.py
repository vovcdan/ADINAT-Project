import tkinter as tk  
from tkinter import Label, messagebox  # Widget
import socket
import threading




# Créer la fenêtre
chat = tk.Tk()
chat.title("ADINAT")

# CONNEXION --------------------------------------------------------------------------
#Connexion
connexion = Label(chat, text="Connexion")
connexion.grid(row=0, column=2,pady= 15)
#utilisateur
connexion_util = Label(chat, text="nom d'utilisateur : ")
connexion_util.grid(row=1, column=0, padx=5, pady=5)
util = tk.Entry(chat, width=20)
util.grid(row=1, column=2, padx=5, pady=5)

def connexion_serv():
    # connexion avec le serveur
    host = "localhost" 
    port = 8888 
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    # envoyer le nom d'utilisateur au serveur pour se connecter
    client_socket.sendall("/login".encode())
    #recupere le nom de l'utilisateur saisie
    username = util.get()
    #encoyer le nom de l'util 
    client_socket.sendall(username.encode())
    #recuperer la reponse du serveur de taille 256 et decode les octets
    response = client_socket.recv(256).decode()
    #si pas ok
    if response == "402":
        messagebox.showerror("Erreur", "Ce nom d'utilisateur est déjà utilisé.")
        client_socket.close()
        return
    #si ok
    elif response == "200":
        # changé le label en connecté 
        connexion.config(text="Connecté en tant que " + username)

        # boucle d'écoute pour recevoir les messages du serveur
        while True:
            try :
                message = client_socket.recv(256).decode()
                # afficher le message dans l'interface utilisateur
                chat.insert(tk.END, message)
            except ConnectionResetError:
                break
        client_socket.close()
        chat.quit()


# Créer bouton
bouton = tk.Button(chat, text="Envoyer", command=connexion_serv) 
bouton.grid(row=3, column=3, padx=5, pady=5)


# # CHAT --------------------------------------------------------------------------
# # Créer historique des message en un bloc scrollable
# historique = scrolledtext.ScrolledText(chat, width=50, height=20)
# historique.grid(row=0, column=0, padx=5, pady=5, columnspan=2)
# # Créer le champ de saisie
# message = tk.Entry(chat, width=40)
# message.grid(row=1, column=0, padx=5, pady=5)
# #pouvoir appuyer sur entrée pour envoyer un message
# message.bind("<Return>")  
# # Créer bouton
# bouton = tk.Button(chat, text="Envoyer") #command=envoyerunmessage
# bouton.grid(row=1, column=1, padx=5, pady=5)



# Lancement 
chat.mainloop()