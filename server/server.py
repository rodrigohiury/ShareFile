import threading
import os
import socket
import json
import base64
import hashlib
from dotenv import load_dotenv

load_dotenv()
HOST_SERVIDOR = os.getenv("HOST_SERVIDOR")
PORTA_SERVIDOR = int(os.getenv("PORTA_SERVIDOR"))
TEXT_FORMAT = os.getenv("TEXT_FORMAT")
TAMANHO_BUFFER = int(os.getenv("TAMANHO_BUFFER"))
clients = {}

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST_SERVIDOR, PORTA_SERVIDOR))
server.listen(5)

print(f"[LISTENING] Listening on : {HOST_SERVIDOR}:{PORTA_SERVIDOR}")

def broadcast(message):
    for client in clients:
        try:
            client.send(message.encode('utf-8'))
        except:
            # Se der erro (cliente desconectado), remove da lista
            client.remove(client)

def treat_message(msg):
    msg = msg.strip(" ")
    sender = msg[0]
    file = msg[1]
    receiver = msg[2]
    total_chunks = int(msg[3])
    return sender, file, receiver, total_chunks

def treat_package(package):
    package = json.loads(package)
    id_chunk = package["id_chunk"]
    file_chunk = package["file_chunk"]
    chunk_hash = package["chunk_hash"]
    
    # Decode the file chunk from base64
    file_chunk = base64.b64decode(file_chunk)
    
    return id_chunk, file_chunk, chunk_hash

def packageIsOk(chunck, hash):
    calculated_hash = hashlib.sha256(chunck).hexdigest()
    
    if calculated_hash != hash:
        return False
    return True

def receive_file(sender):
    last_chunk = "-1"
    client = clients[sender][0]
    print(f"[INFO] Waiting for file chunks from {sender}...")
    while True:
        package = client.recv(TAMANHO_BUFFER).decode(TEXT_FORMAT)
        if package == "END\n":
            print("[INFO] File transfer completed.")
            break
        
        package_data = json.loads(package)
        id_chunk = package_data["id_chunk"]
        file_chunk = base64.b64decode(package_data["file_chunk"])
        chunk_hash = package_data["chunk_hash"]
        
        if not packageIsOk(file_chunk, chunk_hash):
            print(f"[ERROR] Chunk {id_chunk} failed hash verification.")
            client.send(f"NACK {last_chunk}\n".encode(TEXT_FORMAT))
            continue
        
        client.send(f"ACK {id_chunk}".encode(TEXT_FORMAT))

        with open(f"received_chunk_{id_chunk}.bin", "wb") as f:
            f.write(file_chunk)
        
        print(f"[INFO] Received chunk {id_chunk} successfully.")

def handle_client(client_socket, client_address):
    username = client_socket.recv(64).decode(TEXT_FORMAT)
    username = username.strip(" ")[0]
    clients[username] = [client_socket, client_address]
    msg_connected = f"[INFO] {username} has joined the server."
    print(msg_connected)
    broadcast(msg_connected)

    connected = True

    while connected:
        msg_size = client_socket.recv(64).decode(TEXT_FORMAT)
        msg_size = int(msg_size)
        if msg_size:
            msg = client_socket.recv(int(msg_size)).decode(TEXT_FORMAT)
            if msg == "END\n":
                print(f"[INFO] {username} has left the server.")
                broadcast(f"[INFO] {username} has left the server.")
                client_socket.send("END\n".encode(TEXT_FORMAT))
                del clients[username]
                client_socket.close()
                connected = False
                break
            sender, file, receiver, total_chuncks = treat_message(msg)
            print(f"[INFO] {sender} wish to send {file} to {receiver}")
            if receiver in clients:
                receiver_socket, receiver_address = clients[receiver]
                receiver_socket.send(f"[RECEIVE] {sender} {file} {total_chuncks}\n".encode(TEXT_FORMAT))
                client_socket.send("ACK -1".encode(TEXT_FORMAT))
                receiving = True
                while receiving:
                    package = client_socket.recv(TAMANHO_BUFFER).decode(TEXT_FORMAT)
                    if package != "END\n":
                        id_chunk, file_chunk, chunk_hash = treat_package(package)
                        if packageIsOk(file_chunk, chunk_hash):
                            receiver_socket.send(package)
                            msg_chunck_ack = f"CHUNCK {id_chunk} ACK"
                            client_socket.send(msg_chunck_ack.encode(TEXT_FORMAT))
                    else:
                        print(f"[INFO] {sender} finished sending {file} to {receiver}")
                        receiver_socket.send("END\n".encode(TEXT_FORMAT))
                        client_socket.send("END\n".encode(TEXT_FORMAT))
                        receiving = False
            else:
                print(f"[ERROR] {receiver} not found. File not sent.")



def start():
    while True:
        client_socket, client_address = server.accept()
        thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        thread.start()
        print(f"[NEW CONNECTION ESTABLISHED] Active connections: {threading.activeCount() - 1}")

start()


