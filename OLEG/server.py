import socket
import pygame
import threading
import time
pygame.mixer.init()
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
port = int(input('Port: '))
# Шаг 2: Привязываем к адресу и порту
server_socket.bind(('0.0.0.0', port))  # 0.0.0.0 = слушать все сетевые интерфейсы
while True:
    # Шаг 3: Начинаем слушать (разрешаем до 5 ожидающих подключений)
    server_socket.listen(5)

    # Шаг 4: Принимаем входящее подключение
    client_socket, client_address = server_socket.accept()  # Программа "застынет" здесь, пока кто-то не подключится

    # Шаг 5: Получаем данные
    data = client_socket.recv(1024)  # Читаем до 1024 байт
    print(f"Получено: {data.decode('utf-8')}")
    if data.decode('utf-8') == 'UwU':
        pygame.mixer.music.load("Дядя_Саша.mp3")
        pygame.mixer.music.play()
    # Шаг 6: Отправляем ответ
    client_socket.send("Сообщение получено!".encode('utf-8'))

# Шаг 7: Закрываем соединение
client_socket.close()
server_socket.close()
