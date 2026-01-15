import socket

def main():
    # 1. Creazione del socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 2. Connessione al server (IP localhost e porta 12345)
    client_socket.connect(("127.0.0.1", 12345))

    # 3. Invio di un messaggio
    connesso = True
    while connesso:
        msg= input("Inserisci un messaggio ")
        client_socket.send(msg.encode())

        # 4. Ricezione risposta
        data = client_socket.recv(1024).decode()
        if data != None:
            if data.strip().lower() != "fine":
                print(f"Risposta dal server: {data}")
            else:
                connesso = False
        else:
            continue
        # 5. Chiusura connessione
    client_socket.close()
main()