import asyncio
import pygame
import ctypes
import os
<<<<<<< Updated upstream

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
                        client_writer.write(f"{name}: {message}".encode('utf-8'))
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
        try:
            await writer.wait_closed()
        except Exception as e:
            print(e)
            writer.close()

async def start_server():
    port = int(input('Port: '))
    server = await asyncio.start_server(
        handle_client,
        '0.0.0.0',
        port
    )
    print(f"Server started on port: {port}")
    print(f"Ожидание подключений с токеном: {EXPECTED_TOKEN}")
=======
import sys
import shutil
import json
import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

if sys.platform == "win32":
    import ctypes
    ctypes.windll.kernel32.SetConsoleTitleW("O.L.E.G. messenger - Server")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('server_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SERVER')

BANNER = (
    '#####   #       #####   #####\n'
    '#   #   #       #       #    \n'
    '#   #   #       ####    #  ##\n'
    '#   #   #       #       #   #\n'
    '#####   #####   #####   #####\n'
)

CURSOR_HIDE = '\033[?25l'
CURSOR_SHOW = '\033[?25h'
CURSOR_HOME = '\033[H'


class Config:
    """Configuration constants"""
    EXPECTED_TOKEN = "Y2010M07D23.01"
    MAX_MESSAGE_HISTORY = 1000
    MAX_CHAT_HISTORY = 500
    HISTORY_FILE = "server_history.json"
    UPLOADS_FOLDER = "server_uploads"
    MAX_FILE_SIZE = 10 * 1024 * 1024
    BUFFER_SIZE = 1048576  # 1MB
    
    ALLOWED_EXTENSIONS = {
        'images': {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'},
        'documents': {'.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'},
        'archives': {'.zip', '.rar', '.7z', '.tar', '.gz'},
        'code': {'.py', '.js', '.html', '.css', '.json', '.xml', '.md'},
        'other': {'.mp3', '.mp4', '.wav', '.avi', '.mkv'}
    }


class MessageManager:
    """Manages server messages and history"""
    
    def __init__(self):
        logger.debug("Server MessageManager initialized")
        self.text_to_write: List[str] = []
        self.chat_history: List[str] = []
        self.lock = asyncio.Lock()
    
    async def save_history(self):
        """Save chat history to file"""
        logger.debug("MessageManager.save_history() called")
        try:
            async with self.lock:
                with open(Config.HISTORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(
                        self.chat_history[-Config.MAX_CHAT_HISTORY:], 
                        f, 
                        ensure_ascii=False, 
                        indent=2
                    )
            logger.debug(f"MessageManager.save_history() - Saved {len(self.chat_history)} messages")
        except Exception as e:
            logger.error(f"MessageManager.save_history() - Error: {e}")
    
    async def load_history(self):
        """Load chat history from file"""
        logger.debug("MessageManager.load_history() called")
        try:
            if os.path.exists(Config.HISTORY_FILE):
                with open(Config.HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self.chat_history = json.load(f)
                self.text_to_write.extend(self.chat_history[-50:])
                logger.debug(f"MessageManager.load_history() - Loaded {len(self.chat_history)} messages")
            else:
                logger.debug("MessageManager.load_history() - No history file found")
        except Exception as e:
            logger.error(f"MessageManager.load_history() - Error: {e}")
            self.chat_history = []
    
    async def add_message(self, message: str, is_user_message: bool = False):
        """Add a message to display and optionally to history"""
        logger.debug(f"MessageManager.add_message() - Message: '{message[:50]}...', is_user: {is_user_message}")
        async with self.lock:
            timestamp = datetime.now().strftime("[%H:%M:%S]")
            formatted_message = f"{timestamp} {message}"
            self.text_to_write.append(formatted_message)
            
            if is_user_message:
                self.chat_history.append(formatted_message)
                if len(self.chat_history) > Config.MAX_CHAT_HISTORY:
                    self.chat_history = self.chat_history[-Config.MAX_CHAT_HISTORY:]
                await self.save_history()
                logger.debug(f"MessageManager.add_message() - Added to history (total: {len(self.chat_history)})")
            
            if len(self.text_to_write) > Config.MAX_MESSAGE_HISTORY:
                self.text_to_write = self.text_to_write[-Config.MAX_MESSAGE_HISTORY:]
                logger.debug(f"MessageManager.add_message() - Trimmed display messages")
    
    def get_display_messages(self) -> List[str]:
        """Get messages for display"""
        return self.text_to_write[-Config.MAX_MESSAGE_HISTORY:]
    
    async def clear_messages(self):
        """Clear all messages"""
        logger.debug("MessageManager.clear_messages() called")
        async with self.lock:
            self.text_to_write = []


class ClientInfo:
    """Stores client connection information"""
    
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, 
                 name: str, addr: tuple):
        logger.debug(f"ClientInfo created for {name} at {addr}")
        self.reader = reader
        self.writer = writer
        self.name = name
        self.addr = addr
        self.connected_at = datetime.now()
    
    def __repr__(self):
        return f"ClientInfo(name={self.name}, addr={self.addr})"


class ClientManager:
    """Manages all connected clients"""
    
    def __init__(self):
        logger.debug("ClientManager initialized")
        self.clients: List[ClientInfo] = []
        self.lock = asyncio.Lock()
    
    async def add_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, 
                        name: str, addr: tuple):
        """Add a new client"""
        logger.info(f"ClientManager.add_client() - Adding client: {name} at {addr}")
        async with self.lock:
            client = ClientInfo(reader, writer, name, addr)
            self.clients.append(client)
            logger.debug(f"ClientManager.add_client() - Total clients: {len(self.clients)}")
    
    async def remove_client(self, writer: asyncio.StreamWriter):
        """Remove a client"""
        logger.debug(f"ClientManager.remove_client() - Removing client")
        async with self.lock:
            before = len(self.clients)
            self.clients = [c for c in self.clients if c.writer != writer]
            after = len(self.clients)
            logger.debug(f"ClientManager.remove_client() - Removed {before - after} client(s), remaining: {after}")
    
    async def get_all_clients(self) -> List[ClientInfo]:
        """Get all connected clients"""
        async with self.lock:
            return self.clients.copy()
    
    async def get_client_by_name(self, name: str) -> Optional[ClientInfo]:
        """Get client by name"""
        logger.debug(f"ClientManager.get_client_by_name() - Looking for: {name}")
        async with self.lock:
            for client in self.clients:
                if client.name.lower() == name.lower():
                    logger.debug(f"ClientManager.get_client_by_name() - Found: {client}")
                    return client
            logger.debug(f"ClientManager.get_client_by_name() - Not found")
            return None
    
    async def get_client_count(self) -> int:
        """Get number of connected clients"""
        async with self.lock:
            return len(self.clients)


class FileHandler:
    """Handles file operations on server"""
    
    def __init__(self):
        logger.debug("Server FileHandler initialized")
        os.makedirs(Config.UPLOADS_FOLDER, exist_ok=True)
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size for display"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage"""
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._- "
        return ''.join(c for c in filename if c in safe_chars).strip()[:100]
    
    @staticmethod
    def get_file_type(filename: str) -> str:
        """Get file type based on extension"""
        ext = Path(filename).suffix.lower()
        for file_type, extensions in Config.ALLOWED_EXTENSIONS.items():
            if ext in extensions:
                return file_type
        return 'other'
    
    async def handle_file_transfer(self, file_data: str, sender_name: str) -> tuple:
        """
        Handle incoming file transfer
        Returns: (file_content, file_info_json) or (None, error_message)
        """
        logger.info(f"FileHandler.handle_file_transfer() - Sender: {sender_name}")
        try:
            parts = file_data.split('|', 2)
            logger.debug(f"FileHandler.handle_file_transfer() - Parts count: {len(parts)}")
            
            if len(parts) < 3:
                logger.error(f"FileHandler.handle_file_transfer() - Invalid format: {len(parts)} parts")
                return None, "Invalid file format"
            
            filename = self.sanitize_filename(parts[0])
            file_content = parts[1]
            
            logger.debug(f"FileHandler.handle_file_transfer() - Filename: {filename}")
            
            if not filename:
                logger.error("FileHandler.handle_file_transfer() - Empty filename")
                return None, "Invalid filename"
            
            try:
                decoded_content = base64.b64decode(file_content)
                logger.debug(f"FileHandler.handle_file_transfer() - Decoded {len(decoded_content)} bytes")
            except Exception as e:
                logger.error(f"FileHandler.handle_file_transfer() - Base64 decode error: {e}")
                return None, f"Base64 decode error: {e}"
            
            file_size = len(decoded_content)
            logger.debug(f"FileHandler.handle_file_transfer() - File size: {file_size} bytes")
            
            if file_size > Config.MAX_FILE_SIZE:
                logger.error(f"FileHandler.handle_file_transfer() - File too large: {file_size}")
                return None, f"File too large! Max size: {self.format_file_size(Config.MAX_FILE_SIZE)}"
            
            file_type = self.get_file_type(filename)
            human_size = self.format_file_size(file_size)
            logger.debug(f"FileHandler.handle_file_transfer() - Type: {file_type}, Size: {human_size}")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(Config.UPLOADS_FOLDER, safe_filename)
            logger.debug(f"FileHandler.handle_file_transfer() - Saving to: {file_path}")
            
            try:
                with open(file_path, 'wb') as f:
                    f.write(decoded_content)
                logger.info(f"FileHandler.handle_file_transfer() - File saved successfully")
            except Exception as e:
                logger.error(f"FileHandler.handle_file_transfer() - Save error: {e}")
                return None, f"Failed to save file: {e}"
            
            file_info = {
                'type': 'file',
                'filename': safe_filename,
                'original_name': filename,
                'size': human_size,
                'file_type': file_type,
                'sender': sender_name,
                'timestamp': datetime.now().strftime("[%H:%M:%S]")
            }
            
            logger.info(f"FileHandler.handle_file_transfer() - File info: {file_info}")
            return file_content, json.dumps(file_info)
            
        except Exception as e:
            logger.error(f"FileHandler.handle_file_transfer() - Error: {e}", exc_info=True)
            return None, f"File transfer error: {e}"

>>>>>>> Stashed changes

class CommandHandler:
    """Handles server-side commands"""
    
    def __init__(self, client_manager: ClientManager, message_manager: MessageManager):
        logger.debug("Server CommandHandler initialized")
        self.client_manager = client_manager
        self.message_manager = message_manager
    
    async def handle_command(self, command: str, writer: asyncio.StreamWriter, client_name: str):
        """Handle a command from client"""
        logger.debug(f"CommandHandler.handle_command() - Command: '{command}' from {client_name}")
        try:
            parts = command.split(' ', 1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            logger.debug(f"CommandHandler.handle_command() - Parsed: cmd={cmd}, args={args}")
            
            if cmd == '/help':
                await self._cmd_help(writer)
            
            elif cmd == '/users':
                await self._cmd_users(writer)
            
            elif cmd == '/clear':
                await self._cmd_clear(writer)
            
            elif cmd == '/pm':
                await self._cmd_pm(writer, client_name, args)
            
            else:
                logger.warning(f"CommandHandler.handle_command() - Unknown command: {cmd}")
                writer.write(f"Unknown command: {cmd}".encode('utf-8'))
                await writer.drain()
                
        except Exception as e:
            logger.error(f"CommandHandler.handle_command() - Error: {e}", exc_info=True)
            writer.write(f"Command error: {e}".encode('utf-8'))
            await writer.drain()
    
    async def _cmd_help(self, writer: asyncio.StreamWriter):
        """Handle /help command"""
        logger.debug("CommandHandler._cmd_help() called")
        help_text = (
            "Available commands:\n"
            "/help - Show this help message\n"
            "/users - List all connected users\n"
            "/clear - Clear your chat history\n"
            "/pm <username> <message> - Send private message\n"
            "/file <filepath> - Send a file to all users\n"
            "/img <filepath> - Send an image to all users\n"
            "/drop - Open drag & drop window"
        )
        writer.write(help_text.encode('utf-8'))
        await writer.drain()
        logger.info("CommandHandler._cmd_help() - Help sent")
    
    async def _cmd_users(self, writer: asyncio.StreamWriter):
        """Handle /users command"""
        logger.debug("CommandHandler._cmd_users() called")
        clients = await self.client_manager.get_all_clients()
        users_list = ", ".join([c.name for c in clients])
        msg = f"Connected users ({len(clients)}): {users_list}"
        writer.write(msg.encode('utf-8'))
        await writer.drain()
        logger.info(f"CommandHandler._cmd_users() - Sent: {msg}")
    
    async def _cmd_clear(self, writer: asyncio.StreamWriter):
        """Handle /clear command"""
        logger.debug("CommandHandler._cmd_clear() called")
        writer.write("__CLEAR__".encode('utf-8'))
        await writer.drain()
        logger.info("CommandHandler._cmd_clear() - Clear signal sent")
    
    async def _cmd_pm(self, writer: asyncio.StreamWriter, client_name: str, args: str):
        """Handle /pm command"""
        logger.debug(f"CommandHandler._cmd_pm() - Args: '{args}'")
        
        pm_parts = args.split(' ', 1)
        
        if len(pm_parts) < 2:
            logger.warning("CommandHandler._cmd_pm() - Invalid usage")
            writer.write("Usage: /pm <username> <message>".encode('utf-8'))
            await writer.drain()
            return
            
        target_name = pm_parts[0]
        pm_message = pm_parts[1]
        
        logger.debug(f"CommandHandler._cmd_pm() - To: {target_name}, Message: {pm_message}")
        
        target_client = await self.client_manager.get_client_by_name(target_name)
        
        if target_client:
            private_msg = f"[PM from {client_name}]: {pm_message}"
            try:
                target_client.writer.write(private_msg.encode('utf-8'))
                await target_client.writer.drain()
                await self.message_manager.add_message(
                    f"{client_name} -> {target_name}: {pm_message}", 
                    is_user_message=True
                )
                writer.write(f"[PM to {target_name}]: {pm_message}".encode('utf-8'))
                await writer.drain()
                logger.info(f"CommandHandler._cmd_pm() - PM sent to {target_name}")
            except Exception as e:
                logger.error(f"CommandHandler._cmd_pm() - Send error: {e}")
                writer.write(f"Failed to send PM to {target_name}".encode('utf-8'))
                await writer.drain()
        else:
            logger.warning(f"CommandHandler._cmd_pm() - User not found: {target_name}")
            writer.write(f"User '{target_name}' not found".encode('utf-8'))
            await writer.drain()


class ChatServer:
    """Main server class"""
    
    def __init__(self):
        logger.info("ChatServer initialized")
        self.message_manager = MessageManager()
        self.client_manager = ClientManager()
        self.file_handler = FileHandler()
        self.command_handler: Optional[CommandHandler] = None
        self.port = 0
        self.server = None
    
    def _clear_screen(self):
        """Clear console screen"""
        logger.debug("ChatServer._clear_screen() called")
        os.system("cls" if sys.platform == "win32" else "clear")
    
    def _display_banner(self):
        """Display banner"""
        logger.debug("ChatServer._display_banner() called")
        print(BANNER)
        print('=====The Server side=====')
        
        display_messages = self.message_manager.get_display_messages()
        for line in display_messages:  
            print(line)
        
        sys.stdout.write(CURSOR_SHOW)
        sys.stdout.flush()
    
    def _get_port(self) -> int:
        """Get port from user"""
        logger.debug("ChatServer._get_port() called")
        try:
            port = int(input('Port: '))
            logger.debug(f"ChatServer._get_port() - Port: {port}")
            return port
        except ValueError as e:
            logger.error(f"ChatServer._get_port() - Invalid port: {e}")
            print("Invalid port number.")
            return 0
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a client connection"""
        client_addr = writer.get_extra_info('peername')
        logger.info(f"ChatServer._handle_client() - New connection from {client_addr}")
        
        await self.message_manager.add_message(
            f"New connection from {client_addr}", 
            is_user_message=False
        )
        
        client_added = False
        client_name = "Unknown"
        
        try:
            # Authenticate with token
            logger.debug(f"ChatServer._handle_client() - Reading token from {client_addr}")
            token_data = await reader.read(Config.BUFFER_SIZE)
            
            if not token_data:
                logger.warning(f"ChatServer._handle_client() - No token from {client_addr}")
                await self.message_manager.add_message(
                    f"Client {client_addr} disconnected before sending token", 
                    is_user_message=False
                )
                return
                
            received_token = token_data.decode('utf-8').strip()
            logger.debug(f"ChatServer._handle_client() - Received token: '{received_token}'")
            
            if received_token != Config.EXPECTED_TOKEN:
                logger.warning(f"ChatServer._handle_client() - Invalid token from {client_addr}")
                error_msg = "Authentication error: invalid token"
                writer.write(error_msg.encode('utf-8'))
                await writer.drain()
                await self.message_manager.add_message(
                    f"Client {client_addr} disconnected: invalid token", 
                    is_user_message=False
                )
                return
            
            logger.info(f"ChatServer._handle_client() - Token authenticated for {client_addr}")
            await self.message_manager.add_message(
                f"Client {client_addr} authenticated successfully", 
                is_user_message=False
            )
            
            # Get username
            logger.debug(f"ChatServer._handle_client() - Reading username from {client_addr}")
            name_data = await reader.read(Config.BUFFER_SIZE)
            
            if not name_data:
                logger.warning(f"ChatServer._handle_client() - No username from {client_addr}")
                await self.message_manager.add_message(
                    f"Client {client_addr} disconnected before sending username", 
                    is_user_message=False
                )
                return
                
            client_name = name_data.decode('utf-8').strip()
            client_name = ''.join(c for c in client_name if c.isalnum() or c in ' ._-' )[:30]
            
            if not client_name:
                client_name = "Anonymous"
            
            logger.info(f"ChatServer._handle_client() - Username: {client_name}")
            
            if sys.platform == "win32":
                ctypes.windll.kernel32.SetConsoleTitleW(
                    f"O.L.E.G. messenger | Client: {client_name}"
                )
            
            # Add client to manager
            await self.client_manager.add_client(reader, writer, client_name, client_addr)
            client_added = True
            
            current_count = await self.client_manager.get_client_count()
            await self.message_manager.add_message(
                f"{client_name} Connected. Total Clients: {current_count}", 
                is_user_message=False
            )
            logger.info(f"ChatServer._handle_client() - {client_name} connected ({current_count} total)")
            
            # Broadcast join message
            join_msg = f"*** {client_name} has joined the chat ***"
            await self._broadcast_message(join_msg, writer)

            # Main message loop
            logger.info(f"ChatServer._handle_client() - Starting message loop for {client_name}")
            while True:
                data = await reader.read(Config.BUFFER_SIZE)
                
                if not data:
                    logger.info(f"ChatServer._handle_client() - Client {client_name} disconnected")
                    break
                
                message = data.decode('utf-8').strip()
                logger.debug(f"ChatServer._handle_client() - Received from {client_name}: '{message[:100]}...'")
                
                if not message:
                    continue

                # Handle file transfer
                if message.startswith('__FILE__|'):
                    logger.debug(f"ChatServer._handle_client() - File transfer from {client_name}")
                    file_data = message[9:]
                    file_content, result = await self.file_handler.handle_file_transfer(
                        file_data, client_name
                    )
                    
                    if result.startswith('{'):
                        logger.info(f"ChatServer._handle_client() - File saved from {client_name}")
                        await self._broadcast_message(f"__FILE_INFO__|{result}", writer)
                        await self.message_manager.add_message(
                            f"{client_name} sent a file", 
                            is_user_message=True
                        )
                    else:
                        logger.error(f"ChatServer._handle_client() - File error: {result}")
                        writer.write(f"__ERROR__|{result}".encode('utf-8'))
                        await writer.drain()
                    continue

                # Handle commands
                if message.startswith('/'):
                    logger.debug(f"ChatServer._handle_client() - Command from {client_name}")
                    await self.command_handler.handle_command(message, writer, client_name)
                    continue
                
                # Regular message
                timestamp = datetime.now().strftime("[%H:%M:%S]")
                formatted_message = f"{client_name}: {message}"
                
                await self.message_manager.add_message(formatted_message, is_user_message=True)
                logger.info(f"ChatServer._handle_client() - Broadcast: {formatted_message}")
                await self._broadcast_message(formatted_message, writer)

        except Exception as e:
            logger.error(f"ChatServer._handle_client() - Error: {e}", exc_info=True)
            await self.message_manager.add_message(
                f"Error while handling client {client_addr}: {e}", 
                is_user_message=False
            )
        finally:
            if client_added:
                await self.client_manager.remove_client(writer)
                remaining = await self.client_manager.get_client_count()
                timestamp = datetime.now().strftime("[%H:%M:%S]")
                await self.message_manager.add_message(
                    f"{client_name} disconnected. Remaining clients: {remaining}", 
                    is_user_message=False
                )
                logger.info(f"ChatServer._handle_client() - {client_name} disconnected ({remaining} remaining)")
                
                leave_msg = f"*** {client_name} has left the chat ***"
                await self._broadcast_message(leave_msg, None)
                    
            try:
                writer.close()
                await writer.wait_closed()
                logger.debug(f"ChatServer._handle_client() - Writer closed for {client_addr}")
            except Exception as e:
                logger.error(f"ChatServer._handle_client() - Close error: {e}")
    
    async def _broadcast_message(self, message: str, exclude_writer: Optional[asyncio.StreamWriter] = None):
        """Broadcast message to all clients"""
        logger.debug(f"ChatServer._broadcast_message() - Message: '{message[:50]}...'")
        current_clients = await self.client_manager.get_all_clients()
        
        for client in current_clients:
            if client.writer != exclude_writer:
                try:
                    client.writer.write(message.encode('utf-8'))
                    await client.writer.drain()
                    logger.debug(f"ChatServer._broadcast_message() - Sent to {client.name}")
                except Exception as e:
                    logger.warning(f"ChatServer._broadcast_message() - Failed to send to {client.name}: {e}")
                    await self.client_manager.remove_client(client.writer)
    
    async def run(self):
        """Run the server"""
        logger.info("ChatServer.run() started")
        try:
            self._clear_screen()
            self._display_banner()
            
            await self.message_manager.load_history()
            
            self.port = self._get_port()
            if not self.port:
                logger.error("ChatServer.run() - Invalid port")
                return

            self.server = await asyncio.start_server(
                self._handle_client,
                '0.0.0.0',
                self.port
            )
            
            logger.info(f"ChatServer.run() - Server started on port {self.port}")
            
            await self.message_manager.add_message(
                f"Server started on port: {self.port}", 
                is_user_message=False
            )
            await self.message_manager.add_message(
                "Waiting for connections...", 
                is_user_message=False
            )
            await self.message_manager.add_message(
                "Type /help in client for commands", 
                is_user_message=False
            )
            await self.message_manager.add_message(
                f"Max file size: {self.file_handler.format_file_size(Config.MAX_FILE_SIZE)}", 
                is_user_message=False
            )
            
            # Initialize command handler
            self.command_handler = CommandHandler(self.client_manager, self.message_manager)

            async with self.server:
                logger.info("ChatServer.run() - Serving forever")
                await self.server.serve_forever()

        except Exception as e:
            logger.error(f"ChatServer.run() - Fatal error: {e}", exc_info=True)
            print(f"Error occurred: {e}")
        finally:
            logger.info("ChatServer.run() ended")


async def main():
    """Main entry point"""
    logger.info("=" * 50)
    logger.info("SERVER STARTING")
    logger.info("=" * 50)
    
    server = ChatServer()
    await server.run()
    
    logger.info("=" * 50)
    logger.info("SERVER SHUTDOWN")
    logger.info("=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Server interrupted by user")
        print("\nServer stopped.")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\nFatal error: {e}")