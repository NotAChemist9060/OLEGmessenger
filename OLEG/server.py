import asyncio
import os
import sys
from typing import List, Tuple

if sys.platform == "win32":
    import ctypes
    ctypes.windll.kernel32.SetConsoleTitleW("O.L.E.G. messanger")
os.system("cls" if sys.platform == "win32" else "clear")
print(' #####   #       #####   #####\n',
       '#   #   #       #       #    \n',
       '#   #   #       ####    #  ##\n',
       '#   #   #       #       #   #\n',
       '#####   #####   #####   #####\n')
print('=====The Server side=====')

# Expected token - must match exactly with client
EXPECTED_TOKEN = "Y2010M07D23.01"

class ClientManager:
    def __init__(self):
        self.clients = []
        self.lock = asyncio.Lock()
    
    async def add_client(self, reader, writer, name):
        async with self.lock:
            self.clients.append((reader, writer, name))
    
    async def remove_client(self, writer):
        async with self.lock:
            self.clients = [(r, w, n) for r, w, n in self.clients if w != writer]
    
    async def get_all_clients(self):
        async with self.lock:
            return self.clients.copy()

client_manager = ClientManager()

async def handle_client(reader, writer):
    client_addr = writer.get_extra_info('peername')
    print(f"Новое подключение от {client_addr}")
    client_added = False
    
    try:
        # Step 1: Receive and verify token
        token_data = await reader.read(1048576)
        if not token_data:
            print(f"Client {client_addr} disconnected before sending token")
            return
            
        received_token = token_data.decode('utf-8')
        
        # Check if token matches expected value
        if received_token != EXPECTED_TOKEN:
            error_msg = "Authentication error: invalid token"
            writer.write(error_msg.encode('utf-8'))
            await writer.drain()
            print(f"Client {client_addr} disconnected: invalid token")
            return
        
        # Token is valid - continue processing
        print(f"Client {client_addr} authenticated successfully")
        
        # Step 2: Get username
        name_data = await reader.read(1048576)
        if not name_data:
            print(f"Client {client_addr} disconnected before sending username")
            return
            
        name = name_data.decode('utf-8')
        # Sanitize name for security
        name = ''.join(c for c in name if c.isalnum() or c in ' ._-' )[:30]
        
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(f"O.L.E.G. messanger | Client: {name}")
        
        await client_manager.add_client(reader, writer, name)
        client_added = True
        print(f"{name} Connected. Clients: {len(await client_manager.get_all_clients())}")

        # Main message handling loop
        while True:
            data = await reader.read(1048576)
            if not data:
                break
            
            message = data.decode('utf-8')
            # Sanitize message for security
            message = message.replace('\n', ' ').replace('\r', '')[:1000]
            
            print(f"{name}: {message}")
            
            # Get current clients list
            current_clients = await client_manager.get_all_clients()
            
            for client_reader, client_writer, client_name in current_clients:
                if client_writer != writer:
                    try:
                        safe_message = f"{name}: {message}"
                        client_writer.write(safe_message.encode('utf-8'))
                        await client_writer.drain()
                    except Exception:
                        # Remove client if write fails
                        await client_manager.remove_client(client_writer)
                        continue

    except Exception as e:
        print(f"Error while handling client: {e}")
    finally:
        # Remove client from list if it was added
        if client_added:
            await client_manager.remove_client(writer)
            print(f"Client disconnected. Remaining clients: {len(await client_manager.get_all_clients())}")
                
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            # Ignore errors during closing
            pass

async def start_server():
    port = int(input('Port: '))
    server = await asyncio.start_server(
        handle_client,
        '0.0.0.0',
        port
    )
    print(f"Server started on port: {port}")
    print(f"Waiting for connections...")

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("Server stopped.")