import socket
import threading
import sys

class AuraChatClient:
    def __init__(self):
        self.client_socket = None
        self.connected = False
        self.in_chat = False
        self.username = ""
        self.receiving = True
        
    def connect(self, host="127.0.0.1", port=12345):
        """Connette al server"""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            self.connected = True
            
            # Ricevi richiesta username
            data = self.client_socket.recv(1024).decode()
            if data.startswith("USERNAME:"):
                self.username = input("Inserisci il tuo username: ")
                self.client_socket.send(self.username.encode())
            
            # Ricevi messaggio benvenuto
            welcome = self.client_socket.recv(1024).decode()
            print(welcome)
            print("\nDigita 'HELP' per vedere i comandi disponibili\n")
            
            # Thread per ricevere messaggi asincroni (chat e notifiche)
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
            return True
        except Exception as e:
            print(f"Errore connessione: {e}")
            return False
    
    def receive_messages(self):
        """Riceve messaggi asincroni dal server"""
        while self.connected and self.receiving:
            try:
                data = self.client_socket.recv(1024).decode()
                if data:
                    # Gestisci messaggi di chat
                    if data.startswith("\nCHAT_MSG:"):
                        # Formato: \nCHAT_MSG:username:messaggio\n
                        parts = data.replace("\nCHAT_MSG:", "").strip().split(":", 1)
                        if len(parts) == 2:
                            sender, message = parts
                            print(f"\n{sender}: {message}")
                            if self.in_chat:
                                print("> ", end="", flush=True)
                    
                    # Gestisci notifiche di sistema
                    elif data.startswith("\nCHAT_NOTIFY:"):
                        # Formato: \nCHAT_NOTIFY:messaggio\n
                        notify = data.replace("\nCHAT_NOTIFY:", "").strip()
                        print(f"\n[SYSTEM] {notify}")
                        if not self.in_chat:
                            print("> ", end="", flush=True)
                    
                    # Ignora altri messaggi (gestiti sincroni)
                    
            except:
                break
    
    def send_command(self, command):
        """Invia comando al server e attende risposta"""
        try:
            self.client_socket.send(command.encode())
            
            # Per messaggi di chat, non attendere risposta sincrona
            if self.in_chat and not command.upper().startswith("/"):
                return True
            
            # Attendi risposta per comandi
            data = self.client_socket.recv(1024).decode()
            
            if data == "DISCONNECT":
                print("\nDisconnessione dal server...")
                return False
            
            if data.startswith("DISCONNECTED:"):
                print(f"\n{data}")
                return False
            
            # Gestisci apertura/chiusura chat
            if data.startswith("[SYSTEM] Chat aperta"):
                self.in_chat = True
                print(f"\n{data}")
                print("\n--- Modalità Chat Attiva ---")
                print("Scrivi i tuoi messaggi e premi INVIO per inviarli")
                print("Digita /EXIT per chiudere la chat\n")
            elif data.startswith("[SYSTEM] Chat chiusa"):
                self.in_chat = False
                print(f"\n{data}\n")
            else:
                # Stampa risposta normale
                print(f"\n{data}\n")
            
            return True
            
        except Exception as e:
            print(f"\nErrore invio comando: {e}")
            return False
    
    def show_help(self):
        """Mostra comandi disponibili"""
        help_text = """
╔══════════════════════════════════════════════════════════════════╗
║                    COMANDI AURACHAT                              ║
╚══════════════════════════════════════════════════════════════════╝

📋 COMANDI INFORMATIVI:
  TIME                    - Mostra l'ora del server
  NAME                    - Mostra il nome del server
  LOG                     - Mostra gli ultimi 10 log del sistema
  
📊 COMANDO INFO:
  INFO                    - Mostra tutte le informazioni
  INFO 1                  - Numero di client connessi
  INFO 2                  - Numero di utenti registrati
  INFO 3                  - Informazioni di rete del server
  INFO 4                  - Informazioni di rete del tuo client
  INFO 5                  - Lista utenti disponibili per chat

💾 ESPORTAZIONE LOG:
  EX [formato] [n] [who]  - Esporta i log
    formato: xml, csv o txt (default: txt)
    n: numero di log da esportare (opzionale, default: tutti)
    who: ALL, CLIENT o SERVER (default: ALL)
  
  Esempi:
    EX                    - Esporta tutti i log in formato txt
    EX xml 50             - Esporta ultimi 50 log in XML
    EX csv 100 CLIENT     - Esporta ultimi 100 log dei client in CSV

💬 COMANDI CHAT:
  USERSLIST               - Mostra utenti disponibili per chattare
  CHAT [username]         - Apri una chat con l'utente specificato
  
  Durante una chat:
    /EXIT                 - Chiudi la chat corrente
  
  CHAT_EX [formato]       - Esporta la chat corrente
    formato: xml, csv o txt (default: txt)

🚪 DISCONNESSIONE:
  EXIT                    - Disconnetti dal server

❓ AIUTO:
  HELP                    - Mostra questo menu

╔══════════════════════════════════════════════════════════════════╗
║ Suggerimento: Tutti i comandi sono case-insensitive             ║
╚══════════════════════════════════════════════════════════════════╝
"""
        print(help_text)
    
    def run(self):
        """Loop principale"""
        if not self.connect():
            return
        
        try:
            while self.connected:
                try:
                    if self.in_chat:
                        # Modalità chat: ogni riga è un messaggio
                        print("> ", end="", flush=True)
                        msg = input()
                        
                        if not msg.strip():
                            continue
                        
                        # Invia messaggio
                        if not self.send_command(msg):
                            break
                        
                        # Se ha chiuso la chat, torna al prompt normale
                        if msg.upper() == "/EXIT":
                            self.in_chat = False
                    else:
                        # Modalità comando normale
                        print("> ", end="", flush=True)
                        command = input()
                        
                        if not command.strip():
                            continue
                        
                        if command.upper() == "HELP":
                            self.show_help()
                            continue
                        
                        if not self.send_command(command):
                            break
                        
                        if command.upper() == "EXIT":
                            break
                
                except EOFError:
                    break
        
        except KeyboardInterrupt:
            print("\n\nInterrotto dall'utente")
        
        finally:
            self.receiving = False
            self.connected = False
            if self.client_socket:
                try:
                    self.client_socket.close()
                except:
                    pass
            print("\nDisconnesso.")

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║                       AURACHAT CLIENT                            ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")
    
    client = AuraChatClient()
    client.run()
