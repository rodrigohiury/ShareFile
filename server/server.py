from dotenv import load_dotenv
import os
import socket

load_dotenv()

def run():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((os.getenv("HOST_SERVIDOR"), os.getenv("PORTA_SERVIDOR")))