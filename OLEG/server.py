import socket
import asyncio
import pygame
import threading
import ctypes
import os


pygame.mixer.init()
ctypes.windll.kernel32.SetConsoleTitleW("O.L.E.G. messanger")
os.system('cls||clear')
print(' #####   #       #####   #####\n',
       '#   #   #       #       #    \n',
       '#   #   #       ####    #  ##\n',
       '#   #   #       #       #   #\n',
       '#####   #####   #####   #####\n')
print('=====The Server side=====')
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
port = int(input('Port: '))
server_socket.bind(('0.0.0.0', port))
server_socket.listen(5)

def handle_client(client_socket, client_address):
    try:
        name = client_socket.recv(1024)
        ctypes.windll.kernel32.SetConsoleTitleW("O.L.E.G. messanger, " + name.decode('utf-8'))
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            print(name.decode('utf-8') + ": " + data.decode('utf-8'))
            client_socket.send("Сообщение получено!".encode('utf-8'))
    except Exception as e:
        print("Error occurred:", e)
    finally:
        client_socket.close()

client_socket, client_address = server_socket.accept()
handle_client(client_socket, client_address)

server_socket.close()