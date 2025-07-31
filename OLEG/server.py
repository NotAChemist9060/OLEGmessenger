import socket
import pygame
import threading
import ctypes;


pygame.mixer.init()

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
port = int(input('Port: '))
server_socket.bind(('0.0.0.0', port))
server_socket.listen(5)

def play_music():
    pygame.mixer.music.load("UwU.mp3")
    pygame.mixer.music.play()

def handle_client(client_socket, client_address):
    try:
        name = client_socket.recv(1024)
        ctypes.windll.kernel32.SetConsoleTitleW("O.L.E.G. messanger, " + name.decode('utf-8'))
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            print(name.decode('utf-8') + ": " + data.decode('utf-8'))
            if data.decode('utf-8') == 'UwU':
                threading.Thread(target=play_music).start()
            client_socket.send("Сообщение получено!".encode('utf-8'))
    except Exception as e:
        print("Error occurred:", e)
    finally:
        client_socket.close()

client_socket, client_address = server_socket.accept()
handle_client(client_socket, client_address)

server_socket.close()