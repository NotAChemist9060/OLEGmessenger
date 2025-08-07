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


active_clients = []

async def handle_client(reader, writer):
    try:
        name_data = await reader.read(1024)
        name = name_data.decode('utf-8')
        ctypes.windll.kernel32.SetConsoleTitleW(f"O.L.E.G. messanger | Client: {name}")
        active_clients.append((reader, writer, name))
        print(f"{name} Connected. Total clients: {len(active_clients)}")

        while True:
            data = await reader.read(1024)
            if not data:
                break
            
            message = data.decode('utf-8')
            print(f"{name}: {message}")

            '''if message == 'UwU':
                asyncio.to_thread(play_music)'''

            # Рассылаем сообщение ВСЕМ клиентам (включая отправителя)
            for client_reader, client_writer, client_name in active_clients:
                try:
                    client_writer.write(f"{name}: {message}\n".encode('utf-8'))
                    await client_writer.drain()
                except:
                    continue

    except Exception as e:
        print(f"Error handling client {name}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()
        active_clients.remove((reader, writer, name))
        print(f"{name} Disconnected. Total clients: {len(active_clients)}")

async def start_server():
    port = int(input('Port: '))
    server = await asyncio.start_server(
        handle_client,
        '0.0.0.0',
        port
    )
    print(f"Server started on port: {port}")

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("Server stopped.")