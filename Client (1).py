import socket
import threading

class AuraChatClient:
    def __init__(self):
        self.client_socket = None
        self.connected = False
        self.in_chat = False
        
    def connect(self, host="127.0.0.1", port=12345):
        """Connette al server"""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            self.connected = True
            
            # Ricevi richiesta username
            data = self.client_socket.recv(1024).decode()
            if data.startswith("USERNAME:"):
                username = input("Inserisci il tuo username: ")
                self.client_socket.send(username.encode())
            
            # Ricevi messaggio benvenuto
            welcome = self.client_socket.recv(1024).decode()
            print(welcome)
            print("\nDigita 'HELP' per vedere i comandi disponibili\n")
            
            # Thread per ricevere messaggi asincroni (chat)
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
            return True
        except Exception as e:
            print(f"Errore connessione: {e}")
            return False
    
    def receive_messages(self):
        """Riceve messaggi asincroni dal server (per chat)"""
        while self.connected:
            try:
                data = self.client_socket.recv(1024).decode()
                if data:
                    # Stampa solo se è un messaggio di chat o notifica
                    if data.startswith("\n"):
                        print(data)
                        if not self.in_chat:
                            print("> ", end="", flush=True)
            except:
                break
    
    def send_command(self, command):
        """Invia comando al server"""
        try:
            self.client_socket.send(command.encode())
            
            # Attendi risposta (solo se non in chat o comando speciale)
            if not command.upper().startswith("CHAT ") or command.upper() == "/EXIT":
                data = self.client_socket.recv(1024).decode()
                
                if data == "DISCONNECT":
                    print("Disconnessione dal server...")
                    return False
                
                if data.startswith("DISCONNECTED:"):
                    print(data)
                    return False
                
                if data.startswith("[SYSTEM] Chat aperta"):
                    self.in_chat = True
                    print(data)
                elif data.startswith("[SYSTEM] Chat chiusa"):
                    self.in_chat = False
                    print(data)
                else:
                    print(data)
            
            return True
        except Exception as e:
            print(f"Errore invio comando: {e}")
            return False
    
    def show_help(self):
        """Mostra comandi disponibili"""
        help_text = """
=== COMANDI AURACHAT ===

TIME                    - Mostra ora del server
NAME                    - Mostra nome del server
INFO [type]             - Mostra informazioni
                          1: Client connessi
                          2: Utenti registrati
                          3: Info rete server
                          4: Info rete client
                          5: Lista utenti disponibili
LOG                     - Mostra ultimi 10 log
EX [xml/csv/txt] [n] [who] - Esporta log
                          n: numero log (opzionale)
                          who: ALL/CLIENT/SERVER (opzionale)
USERSLIST               - Lista utenti per chat
CHAT [username]         - Apri chat con utente
                          (in chat: /EXIT per chiudere)
CHAT_EX [xml/csv/txt]   - Esporta chat corrente
EXIT                    - Disconnetti dal server
HELP                    - Mostra questo aiuto
"""
        print(help_text)
    
    def run(self):
        """Loop principale"""
        if not self.connect():
            return
        
        try:
            while self.connected:
                if self.in_chat:
                    msg = input()
                    if not self.send_command(msg):
                        break
                    if msg.upper() == "/EXIT":
                        self.in_chat = False
                else:
                    command = input("> ")
                    
                    if not command.strip():
                        continue
                    
                    if command.upper() == "HELP":
                        self.show_help()
                        continue
                    
                    if not self.send_command(command):
                        break
                    
                    if command.upper() == "EXIT":
                        break
        
        except KeyboardInterrupt:
            print("\n\nInterrotto dall'utente")
        
        finally:
            self.connected = False
            if self.client_socket:
                self.client_socket.close()
            print("Disconnesso.")

if __name__ == "__main__":
    client = AuraChatClient()
    client.run()