import socket
import threading
import datetime

    # 1. Creazione del socket TCP (IPv4 + TCP)
def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("127.0.0.1", 12345))
    # 3. Mettere il server in ascolto
    server_socket.listen(5)
    print("Server in ascolto sulla porta 12345...")
    while True:# 4. Attesa di una connessione da parte del client
        client_socket, client_address = server_socket.accept()
        thread = threading.Thread(target= gestione,args=(client_socket,client_address))
        thread.start()

def gestione(client_socket,client_address):
    attivo = True
    print(f"Connessione da {client_address}")
    while attivo:    
        # 5. Ricezione messaggio dal client
        data = client_socket.recv(1024).decode()
        if data != None:
            if data.upper().strip()!= "EXIT":
            # 6. Risposta al client 
                if data.upper().strip() == "TIME":
                    client_socket.send(f"{time()}".encode())
                elif data.upper().strip() == "NAME":
                    client_socket.send(f"{name()}".encode())
                else:
                    print(f"Messaggio ricevuto: {data}")
                    client_socket.send(f"Ciao {client_address}, ho ricevuto il tuo messaggio!.".encode())
            else:
                client_socket.send(f"fine".encode())
                attivo = False

    # 7. Chiusura connessione con il client
    client_socket.close()

def time():
    data = datetime.datetime.now()
    ora = ""
    #formatta l'orario sempre alla stessa grandezza
    if len(str(data.hour)) < 2:
        ora+="0"+str(data.hour)
    else:
        ora+=str(data.hour)
    ora+=":"
    if len(str(data.minute)) < 2:
        ora+="0"+str(data.minute)
    else:
        ora+=str(data.minute)
    ora+=":"
    if len(str(data.second)) < 2:
        ora+="0"+str(data.second)
    else:
        ora += str(data.second)
    return ora

def name():
    return socket.gethostname()

main()