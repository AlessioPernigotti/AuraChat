import socket
import threading
import datetime
import json
import os
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import time
import csv

class AuraChatServer:
    def __init__(self):
        self.server_socket = None
        self.clients = {}  # {client_socket: {"address": addr, "username": name, "last_activity": time}}
        self.users_db = {}  # Database utenti permanenti
        self.logs = []
        self.active_chats = {}  # {username: target_username}
        self.chat_messages = {}  # {(user1, user2): [messages]}
        self.lock = threading.Lock()
        
        # Crea struttura cartelle
        if not os.path.exists("util"):
            os.makedirs("util")
        
        self.load_config()
        self.load_logs()
        
    def load_config(self):
        """Carica configurazione e database utenti"""
        config_path = "util/config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.users_db = config.get("users", {})
        else:
            # Crea config di default
            config = {
                "server_port": 12345,
                "inactivity_timeout": 120,
                "users": {}
            }
            self.save_config(config)
    
    def save_config(self, config=None):
        """Salva configurazione"""
        if config is None:
            config = {
                "server_port": 12345,
                "inactivity_timeout": 120,
                "users": self.users_db
            }
        with open("util/config.json", 'w') as f:
            json.dump(config, f, indent=4)
    
    def load_logs(self):
        """Carica log da XML"""
        log_path = "util/log.xml"
        if os.path.exists(log_path):
            try:
                tree = ET.parse(log_path)
                root = tree.getroot()
                for log in root.findall("log"):
                    self.logs.append({
                        "timestamp": log.find("timestamp").text,
                        "type": log.find("type").text,
                        "user": log.find("user").text,
                        "message": log.find("message").text
                    })
            except:
                pass
    
    def save_logs(self):
        """Salva log in XML"""
        root = ET.Element("logs")
        for log in self.logs:
            log_elem = ET.SubElement(root, "log")
            ET.SubElement(log_elem, "timestamp").text = log["timestamp"]
            ET.SubElement(log_elem, "type").text = log["type"]
            ET.SubElement(log_elem, "user").text = log["user"]
            ET.SubElement(log_elem, "message").text = log["message"]
        
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        with open("util/log.xml", "w") as f:
            f.write(xml_str)
    
    def add_log(self, log_type, user, message):
        """Aggiunge un log"""
        with self.lock:
            self.logs.append({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": log_type,
                "user": user,
                "message": message
            })
            self.save_logs()
    
    def register_user(self, username, address):
        """Registra un nuovo utente o aggiorna esistente"""
        if username not in self.users_db:
            self.users_db[username] = {
                "id": len(self.users_db) + 1,
                "username": username,
                "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_login": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            self.users_db[username]["last_login"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_config()
    
    def start(self):
        """Avvia il server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(("0.0.0.0", 12345))
        self.server_socket.listen(5)
        print("AURACHAT Server in ascolto sulla porta 12345...")
        self.add_log("SERVER", "SYSTEM", "Server avviato")
        
        # Thread per controllo inattività
        threading.Thread(target=self.check_inactivity, daemon=True).start()
        
        while True:
            client_socket, client_address = self.server_socket.accept()
            thread = threading.Thread(target=self.handle_client, args=(client_socket, client_address))
            thread.start()
    
    def check_inactivity(self):
        """Controlla inattività client e disconnette dopo 2 minuti"""
        while True:
            time.sleep(10)
            current_time = time.time()
            disconnected = []
            
            with self.lock:
                for client_socket, info in list(self.clients.items()):
                    if current_time - info["last_activity"] > 120:  # 2 minuti
                        disconnected.append((client_socket, info["username"]))
            
            for client_socket, username in disconnected:
                try:
                    client_socket.send("DISCONNECTED: Inattività superata (2 minuti)".encode())
                    client_socket.close()
                except:
                    pass
                with self.lock:
                    if client_socket in self.clients:
                        del self.clients[client_socket]
                self.add_log("SERVER", username, "Disconnesso per inattività")
                print(f"Client {username} disconnesso per inattività")
    
    def handle_client(self, client_socket, client_address):
        """Gestisce un client"""
        username = None
        try:
            # Richiedi username
            client_socket.send("USERNAME:".encode())
            username = client_socket.recv(1024).decode().strip()
            
            if not username:
                client_socket.close()
                return
            
            # Registra utente
            self.register_user(username, client_address)
            
            with self.lock:
                self.clients[client_socket] = {
                    "address": client_address,
                    "username": username,
                    "last_activity": time.time()
                }
            
            self.add_log("CLIENT", username, f"Connesso da {client_address}")
            print(f"Client {username} connesso da {client_address}")
            client_socket.send(f"Benvenuto su AURACHAT, {username}!".encode())
            
            while True:
                data = client_socket.recv(1024).decode().strip()
                
                if not data:
                    break
                
                # Aggiorna attività
                with self.lock:
                    if client_socket in self.clients:
                        self.clients[client_socket]["last_activity"] = time.time()
                
                # Controlla se in chat
                if username in self.active_chats:
                    response = self.handle_chat_message(username, data)
                else:
                    response = self.handle_command(client_socket, username, data)
                
                if response:
                    client_socket.send(response.encode())
                
                if data.upper() == "EXIT":
                    break
        
        except Exception as e:
            print(f"Errore con client {username}: {e}")
        
        finally:
            with self.lock:
                if client_socket in self.clients:
                    del self.clients[client_socket]
                if username and username in self.active_chats:
                    del self.active_chats[username]
            
            if username:
                self.add_log("CLIENT", username, "Disconnesso")
            client_socket.close()
    
    def handle_chat_message(self, username, message):
        """Gestisce messaggi in chat"""
        if message.upper() == "/EXIT":
            target = self.active_chats[username]
            del self.active_chats[username]
            
            # Trova e notifica l'altro utente
            for sock, info in self.clients.items():
                if info["username"] == target:
                    try:
                        sock.send(f"\n[SYSTEM] {username} ha chiuso la chat\n".encode())
                    except:
                        pass
                    break
            
            return "[SYSTEM] Chat chiusa"
        
        target = self.active_chats[username]
        chat_key = tuple(sorted([username, target]))
        
        if chat_key not in self.chat_messages:
            self.chat_messages[chat_key] = []
        
        msg_data = {
            "from": username,
            "to": target,
            "message": message,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.chat_messages[chat_key].append(msg_data)
        
        # Inoltra messaggio
        for sock, info in self.clients.items():
            if info["username"] == target:
                try:
                    sock.send(f"\n{username}: {message}\n".encode())
                except:
                    pass
                break
        
        return None  # Non rispondere al mittente
    
    def handle_command(self, client_socket, username, command):
        """Gestisce comandi"""
        parts = command.split()
        cmd = parts[0].upper()
        
        self.add_log("CLIENT", username, f"Comando: {command}")
        
        if cmd == "TIME":
            return self.get_time()
        
        elif cmd == "NAME":
            return socket.gethostname()
        
        elif cmd == "EXIT":
            return "DISCONNECT"
        
        elif cmd == "LOG":
            return self.get_logs()
        
        elif cmd == "INFO":
            info_type = parts[1] if len(parts) > 1 else None
            return self.get_info(username, info_type)
        
        elif cmd == "EX":
            format_type = parts[1] if len(parts) > 1 else "txt"
            number = int(parts[2]) if len(parts) > 2 else None
            who = parts[3] if len(parts) > 3 else "ALL"
            return self.export_logs(format_type, number, who)
        
        elif cmd == "USERSLIST":
            return self.get_users_list(username)
        
        elif cmd == "CHAT":
            if len(parts) < 2:
                return "Errore: specifica username destinatario"
            target_username = parts[1]
            return self.open_chat(username, target_username)
        
        elif cmd == "CHAT_EX":
            format_type = parts[1] if len(parts) > 1 else "txt"
            return self.export_chat(username, format_type)
        
        else:
            return f"Comando sconosciuto: {cmd}"
    
    def get_time(self):
        """Restituisce ora corrente"""
        now = datetime.datetime.now()
        return now.strftime("%H:%M:%S")
    
    def get_logs(self):
        """Restituisce ultimi 10 log"""
        result = "=== ULTIMI 10 LOG ===\n"
        for log in self.logs[-10:]:
            result += f"[{log['timestamp']}] {log['type']} - {log['user']}: {log['message']}\n"
        return result
    
    def get_info(self, username, info_type):
        """Restituisce informazioni"""
        if info_type == "1":
            return f"Client connessi: {len(self.clients)}"
        elif info_type == "2":
            return f"Utenti registrati: {len(self.users_db)}"
        elif info_type == "3":
            return f"Server: {socket.gethostname()} - IP: {socket.gethostbyname(socket.gethostname())}"
        elif info_type == "4":
            for sock, info in self.clients.items():
                if info["username"] == username:
                    return f"Client: {info['address']}"
        elif info_type == "5":
            return self.get_users_list(username)
        else:
            result = f"=== INFORMAZIONI SERVER ===\n"
            result += f"Client connessi: {len(self.clients)}\n"
            result += f"Utenti registrati: {len(self.users_db)}\n"
            result += f"Server: {socket.gethostname()}\n"
            return result
    
    def get_users_list(self, current_user):
        """Lista utenti disponibili per chat"""
        result = "=== UTENTI DISPONIBILI ===\n"
        for sock, info in self.clients.items():
            if info["username"] != current_user:
                status = " [IN CHAT]" if info["username"] in self.active_chats else ""
                result += f"- {info['username']}{status}\n"
        return result
    
    def open_chat(self, username, target_username):
        """Apre una chat tra due utenti"""
        # Verifica che target esista ed è connesso
        target_found = False
        for sock, info in self.clients.items():
            if info["username"] == target_username:
                target_found = True
                if target_username in self.active_chats:
                    return f"Errore: {target_username} è già in una chat"
                
                # Apri chat
                self.active_chats[username] = target_username
                self.active_chats[target_username] = username
                
                # Notifica l'altro utente
                try:
                    sock.send(f"\n[SYSTEM] {username} ha aperto una chat con te. Digita /EXIT per chiudere\n".encode())
                except:
                    pass
                
                return f"[SYSTEM] Chat aperta con {target_username}. Digita /EXIT per chiudere"
        
        if not target_found:
            return f"Errore: utente {target_username} non trovato o non connesso"
    
    def export_chat(self, username, format_type):
        """Esporta chat corrente"""
        if username not in self.active_chats:
            return "Errore: non sei in una chat"
        
        target = self.active_chats[username]
        chat_key = tuple(sorted([username, target]))
        
        if chat_key not in self.chat_messages:
            return "Nessun messaggio da esportare"
        
        filename = f"chat_{username}_{target}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}"
        
        if format_type == "txt":
            with open(filename, 'w') as f:
                f.write(f"Chat tra {username} e {target}\n")
                f.write("=" * 50 + "\n\n")
                for msg in self.chat_messages[chat_key]:
                    f.write(f"[{msg['timestamp']}] {msg['from']}: {msg['message']}\n")
        
        elif format_type == "csv":
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "From", "To", "Message"])
                for msg in self.chat_messages[chat_key]:
                    writer.writerow([msg['timestamp'], msg['from'], msg['to'], msg['message']])
        
        elif format_type == "xml":
            root = ET.Element("chat")
            for msg in self.chat_messages[chat_key]:
                msg_elem = ET.SubElement(root, "message")
                ET.SubElement(msg_elem, "timestamp").text = msg['timestamp']
                ET.SubElement(msg_elem, "from").text = msg['from']
                ET.SubElement(msg_elem, "to").text = msg['to']
                ET.SubElement(msg_elem, "text").text = msg['message']
            
            xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
            with open(filename, "w") as f:
                f.write(xml_str)
        
        return f"Chat esportata in {filename}"
    
    def export_logs(self, format_type, number, who):
        """Esporta log"""
        logs_to_export = self.logs[-number:] if number else self.logs
        
        if who == "CLIENT":
            logs_to_export = [l for l in logs_to_export if l["type"] == "CLIENT"]
        elif who == "SERVER":
            logs_to_export = [l for l in logs_to_export if l["type"] == "SERVER"]
        
        filename = f"logs_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}"
        
        if format_type == "txt":
            with open(filename, 'w') as f:
                for log in logs_to_export:
                    f.write(f"[{log['timestamp']}] {log['type']} - {log['user']}: {log['message']}\n")
        
        elif format_type == "csv":
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Type", "User", "Message"])
                for log in logs_to_export:
                    writer.writerow([log['timestamp'], log['type'], log['user'], log['message']])
        
        elif format_type == "xml":
            # Copia già in XML
            root = ET.Element("logs")
            for log in logs_to_export:
                log_elem = ET.SubElement(root, "log")
                ET.SubElement(log_elem, "timestamp").text = log["timestamp"]
                ET.SubElement(log_elem, "type").text = log["type"]
                ET.SubElement(log_elem, "user").text = log["user"]
                ET.SubElement(log_elem, "message").text = log["message"]
            
            xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
            with open(filename, "w") as f:
                f.write(xml_str)
        
        return f"Log esportati in {filename}"

if __name__ == "__main__":
    server = AuraChatServer()
    server.start()