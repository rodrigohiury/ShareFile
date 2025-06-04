import json
import base64
import hashlib
import os
import socket
import threading
from dotenv import load_dotenv

load_dotenv()
HOST_SERVIDOR = os.getenv("HOST_SERVIDOR")
PORTA_SERVIDOR = int(os.getenv("PORTA_SERVIDOR"))
TEXT_FORMAT = os.getenv("TEXT_FORMAT")
TAMANHO_BUFFER = int(os.getenv("TAMANHO_BUFFER"))
PASTA_SHARED = os.getenv("PASTA_SHARED")

client_id = input("Enter your username: ")

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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

def send_file(archive_name, receiver):
    if not os.path.exists(archive_name):
        print(f"[ERROR] File '{archive_name}' does not exist.")
        return

    with open(archive_name, "rb") as file:
        file_content = file.read()
    
    # Split the file into chunks
    chunk_size = TAMANHO_BUFFER
    chunks = [file_content[i:i + chunk_size] for i in range(0, len(file_content), chunk_size)]

    msg = f"[SEND] {client_id} {archive_name} TO {receiver} {len(chunks)}\n"
    msg.encode(TEXT_FORMAT)
    msg_lenght = len(msg)
    send_lenght = str(msg_lenght).encode(TEXT_FORMAT)
    send_lenght += b' ' * (64 - len(send_lenght))
    client.send(send_lenght)
    
    for i, chunk in enumerate(chunks):

        chunk_hash = hashlib.sha256(chunk).hexdigest()
        encoded_chunk = base64.b64encode(chunk).decode(TEXT_FORMAT)
        
        package = {
            "id_chunk": i,
            "file_chunk": encoded_chunk,
            "chunk_hash": chunk_hash,
            "receiver": receiver
        }
        
        package_json = json.dumps(package)
        client.send(package_json.encode(TEXT_FORMAT))
        print(f"[INFO] Sending chunk {i} to {receiver}.")
    
    client.send("!END".encode(TEXT_FORMAT))
    print(f"[INFO] Finished sending file '{archive_name}' to {receiver}.")

def receive_file(total_chunks, filename):
    last_chunk = -1
    received_chunks = {}
    while True:
        package = client.recv(TAMANHO_BUFFER).decode(TEXT_FORMAT)
        if package == "!END":
            print("[INFO] File transfer completed.")
            break
        
        package_data = json.loads(package)
        id_chunk = int(package_data["id_chunk"])
        file_chunk = base64.b64decode(package_data["file_chunk"])
        chunk_hash = package_data["chunk_hash"]
        
        if not packageIsOk(file_chunk, chunk_hash):
            print(f"[ERROR] Chunk {id_chunk} failed hash verification.")
            client.send(f"NACK {last_chunk}\n".encode(TEXT_FORMAT))
            continue
        
        client.send(f"ACK {id_chunk}".encode(TEXT_FORMAT))

        if id_chunk == last_chunk+1:
            received_chunks[id_chunk] = file_chunk
        
        print(f"[INFO] Received chunk {id_chunk} successfully.")

    if len(received_chunks) == total_chunks:
        print("Todos os chunks recebidos. Pronto para remontar.")

    with open(f"{PASTA_SHARED}/{filename}", "wb") as f:
            for i in range(total_chunks):
                f.write(received_chunks[i])

def start():
    while True:
        cmd = input("Enter command: ")
        if cmd == "!END":
            print("[INFO] Ending connection.")
            msg = "!END"
            msg.encode(TEXT_FORMAT)
            msg_lenght = len(msg)
            send_lenght = str(msg_lenght).encode(TEXT_FORMAT)
            send_lenght += b' ' * (64 - len(send_lenght))
            client.send(send_lenght)
            client.send("!END".encode(TEXT_FORMAT))
            break
        if cmd.startswith("SEND"):
            cmd_parts = cmd.split(" ")
            archive_name = cmd_parts[1]
            receiver = cmd_parts[3]
            send_file(archive_name, receiver)
        elif cmd.startswith("[RECEIVE]"):
            cmd_parts = cmd.split(" ")
            total_chunks = int(cmd_parts[3])
            filename = cmd_parts[2]
            receive_file(total_chunks, filename)
        else:
            print("[ERROR] Unknown command. Use 'SEND <filename> TO <receiver>' to send a file or '!END' to exit.")

def startConnection():
    try:
        client.connect((HOST_SERVIDOR, PORTA_SERVIDOR))
        client.send(client_id.encode(TEXT_FORMAT))
        thread = threading.Thread(target=start)
        thread.start()
        print(f"[CONNECTED] Connected to server at {HOST_SERVIDOR}:{PORTA_SERVIDOR}")
        print("To end the connection, type '!END'")
        while True:
            msg = client.recv(64).decode(TEXT_FORMAT)
            if msg.startswith("[INFO]") or msg.startswith("[ERROR]"):
                print(msg)
            elif msg.startswith("!END"):
                client.close()
                break
    except Exception as e:
        print(f"[ERROR] Could not connect to server: {e}")
        return False
    return True

# package = {
#     "id_chunk": id_chunk
#     "file_chunk": file_chunk,
#     chunk_hash: chunk_hash,
#     }

startConnection()