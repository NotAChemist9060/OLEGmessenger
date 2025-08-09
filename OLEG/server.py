import asyncio
import pygame
import ctypes
import os


title="O.L.E.G. server"
pygame.mixer.init()
ctypes.windll.kernel32.SetConsoleTitleW(title)
os.system('cls||clear')
print(' #####   #       #####   #####\n',
       '#   #   #       #       #    \n',
       '#   #   #       ####    #  ##\n',
       '#   #   #       #       #   #\n',
       '#####   #####   #####   #####\n')
print('=====The Server side=====')

active_clients = []

def update_window_title():
    client_names = [name for (_, _, name) in active_clients]
    title = f"O.L.E.G. server | Clients: " + ", ".join(client_names)
    if len(title) > 200:
        title = f"O.L.E.G. server | Clients: " + {len(active_clients)}
    ctypes.windll.kernel32.SetConsoleTitleW(title)
    return title
    
async def handle_client(reader, writer):
    global active_clients
    try:
        name_data = await reader.read(1048576)
        name = name_data.decode('utf-8')
        active_clients.append((reader, writer, name))
        update_window_title()
        print(f"{name} Connected. Clients: {len(active_clients)}")

        while True:
            data = await reader.read(1048576)
            if not data:
                break
            
            message = data.decode('utf-8')
            print(f"{name}: {message}")
            
            active_clients = [(r, w, n) for r, w, n in active_clients if not r.at_eof()]

            for client_reader, client_writer, client_name in active_clients:
                if client_writer != writer:
                    try:
                        client_writer.write(f"{name}: {message}\n".encode('utf-8'))
                        await client_writer.drain()
                    except:
                        continue
 
    except Exception as e:
        print(f"Error while handling client {name}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()
        active_clients = [(r, w, n) for r, w, n in active_clients if (r, w, n) != (reader, writer, name)]
        update_window_title()
        print(f"{name} Disconnected. Clients: {len(active_clients)}")

async def start_server():
    try:
        port = int(input('Port: '))
        server = await asyncio.start_server(
            handle_client,
            '0.0.0.0',
            port
        )
        print(f"Server started on port: {port}")
    except Exception as e:
        print(f"Error while starting server: {e}")

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("Server stopped.")