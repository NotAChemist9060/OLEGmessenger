import asyncio
import pygame
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

# Ожидаемый токен для аутентификации
EXPECTED_TOKEN = "Y2010M07D23.01"
active_clients = []

async def handle_client(reader, writer):
    client_addr = writer.get_extra_info('peername')
    print(f"Новое подключение от {client_addr}")
    
    try:
        # Шаг 1: Получаем и проверяем токен
        token_data = await reader.read(1024)
        if not token_data:
            print(f"Клиент {client_addr} отключился до отправки токена")
            return
            
        received_token = token_data.decode('utf-8')
        
        if received_token != EXPECTED_TOKEN:
            error_msg = "Ошибка аутентификации: неверный токен"
            writer.write(error_msg.encode('utf-8'))
            await writer.drain()
            print(f"Клиент {client_addr} отключен: неверный токен")
            return
        
        # Токен верный - продолжаем обработку
        print(f"Клиент {client_addr} успешно аутентифицирован")
        
        # Шаг 2: Получаем имя пользователя
        name_data = await reader.read(1024)
        if not name_data:
            print(f"Клиент {client_addr} отключился до отправки имени")
            return
            
        name = name_data.decode('utf-8')
        ctypes.windll.kernel32.SetConsoleTitleW(f"O.L.E.G. messanger | Client: {name}")
        active_clients.append((reader, writer, name))
        print(f"{name} Connected. Clients: {len(active_clients)}")

        # Основной цикл обработки сообщений
        while True:
            data = await reader.read(1048576)
            if not data:
                break
            
            message = data.decode('utf-8')
            print(f"{name}: {message}")

            for client_reader, client_writer, client_name in active_clients:
                if client_writer != writer:
                    try:
                        client_writer.write(f"{name}: {message}\n".encode('utf-8'))
                        await client_writer.drain()
                    except:
                        continue

    except Exception as e:
        print(f"Error while handling client: {e}")
    finally:
        # Удаляем клиента из списка если он был добавлен
        for client in active_clients:
            if client[1] == writer:
                active_clients.remove(client)
                print(f"{client[2]} Disconnected. Clients: {len(active_clients)}")
                break
                
        writer.close()
        await writer.wait_closed()

async def start_server():
    port = int(input('Port: '))
    server = await asyncio.start_server(
        handle_client,
        '0.0.0.0',
        port
    )
    print(f"Server started on port: {port}")
    print(f"Ожидание подключений с токеном: {EXPECTED_TOKEN}")

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("Server stopped.")