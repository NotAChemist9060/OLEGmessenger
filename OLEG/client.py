import socket
ip = str(input('Ip: '))
port = int(input('Port: '))
while True:
    # Шаг 1: Создаем сокет
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Шаг 2: Подключаемся к серверу
    client_socket.connect((ip, port))  # IP и порт сервера
    # Шаг 3: Отправляем сообщение
    message = input()
    if message == '':
        message = 'пустое сообщение отправитель долбаеб'
    elif message == ':exit:':
        break
    client_socket.send(message.encode('utf-8'))  # Преобразуем текст в байты
    # Шаг 4: Получаем ответ
    response = client_socket.recv(1024)

# Шаг 5: Закрываем соединение
client_socket.close()
