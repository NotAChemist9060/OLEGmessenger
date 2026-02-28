import asyncio
import os
import sys
import json
import base64
import logging
import ctypes
from datetime import datetime
from pathlib import Path
from typing import Optional, List

if sys.platform == "win32":
    try:
        ctypes.windll.kernel32.SetConsoleTitleW("O.L.E.G. messenger - Server")
    except Exception:
        pass

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

CURSOR_SHOW = '\033[?25h'


class Config:
    """Configuration constants"""
    EXPECTED_TOKEN = "Y2010M07D23.01"
    MAX_MESSAGE_HISTORY = 1000
    MAX_CHAT_HISTORY = 500
    HISTORY_FILE = "server_history.json"
    UPLOADS_FOLDER = "server_uploads"
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
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
        logger.debug("MessageManager initialized")
        self.text_to_write: List[str] = []
        self.chat_history: List[str] = []
        self.lock = asyncio.Lock()
    
    async def save_history(self):
        """Save chat history to file"""
        try:
            async with self.lock:
                with open(Config.HISTORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(
                        self.chat_history[-Config.MAX_CHAT_HISTORY:], 
                        f, 
                        ensure_ascii=False, 
                        indent=2
                    )
            logger.debug(f"Saved {len(self.chat_history)} messages to history")
        except Exception as e:
            logger.error(f"save_history error: {e}")
    
    async def load_history(self):
        """Load chat history from file"""
        try:
            if os.path.exists(Config.HISTORY_FILE):
                with open(Config.HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self.chat_history = json.load(f)
                self.text_to_write.extend(self.chat_history[-50:])
                logger.debug(f"Loaded {len(self.chat_history)} messages from history")
        except Exception as e:
            logger.error(f"load_history error: {e}")
            self.chat_history = []
    
    async def add_message(self, message: str, is_user_message: bool = False):
        """Add a message to display and optionally to history"""
        async with self.lock:
            timestamp = datetime.now().strftime("[%H:%M:%S]")
            formatted_message = f"{timestamp} {message}"
            self.text_to_write.append(formatted_message)
            
            if is_user_message:
                self.chat_history.append(formatted_message)
                if len(self.chat_history) > Config.MAX_CHAT_HISTORY:
                    self.chat_history = self.chat_history[-Config.MAX_CHAT_HISTORY:]
                await self.save_history()
            
            if len(self.text_to_write) > Config.MAX_MESSAGE_HISTORY:
                self.text_to_write = self.text_to_write[-Config.MAX_MESSAGE_HISTORY:]
    
    def get_display_messages(self) -> List[str]:
        """Get messages for display"""
        return self.text_to_write[-Config.MAX_MESSAGE_HISTORY:]
    
    async def clear_messages(self):
        """Clear all messages"""
        async with self.lock:
            self.text_to_write = []


class ClientInfo:
    """Stores client connection information"""
    
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, 
                 name: str, addr: tuple):
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
        async with self.lock:
            client = ClientInfo(reader, writer, name, addr)
            self.clients.append(client)
            logger.info(f"Added client: {name} at {addr}")
    
    async def remove_client(self, writer: asyncio.StreamWriter):
        """Remove a client"""
        async with self.lock:
            self.clients = [c for c in self.clients if c.writer != writer]
            logger.debug(f"Client removed, remaining: {len(self.clients)}")
    
    async def get_all_clients(self) -> List[ClientInfo]:
        """Get all connected clients"""
        async with self.lock:
            return self.clients.copy()
    
    async def get_client_by_name(self, name: str) -> Optional[ClientInfo]:
        """Get client by name"""
        async with self.lock:
            for client in self.clients:
                if client.name.lower() == name.lower():
                    return client
            return None
    
    async def get_client_count(self) -> int:
        """Get number of connected clients"""
        async with self.lock:
            return len(self.clients)


class FileHandler:
    """Handles file operations on server"""
    
    def __init__(self):
        logger.debug("FileHandler initialized")
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
        try:
            # Parse: filename|base64content
            parts = file_data.split('|', 2)
            
            if len(parts) < 2:
                return None, "Invalid file format"
            
            filename = self.sanitize_filename(parts[0])
            file_content_b64 = parts[1]
            
            if not filename:
                return None, "Invalid filename"
            
            # Decode base64
            try:
                decoded_content = base64.b64decode(file_content_b64)
            except Exception as e:
                return None, f"Base64 decode error: {e}"
            
            file_size = len(decoded_content)
            
            if file_size > Config.MAX_FILE_SIZE:
                return None, f"File too large! Max: {self.format_file_size(Config.MAX_FILE_SIZE)}"
            
            file_type = self.get_file_type(filename)
            human_size = self.format_file_size(file_size)
            
            # Save file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(Config.UPLOADS_FOLDER, safe_filename)
            
            try:
                with open(file_path, 'wb') as f:
                    f.write(decoded_content)
            except Exception as e:
                return None, f"Failed to save file: {e}"
            
            # Build file info for broadcast
            file_info = {
                'type': 'file',
                'filename': safe_filename,
                'original_name': filename,
                'size': human_size,
                'file_type': file_type,
                'sender': sender_name,
                'timestamp': datetime.now().strftime("[%H:%M:%S]")
            }
            
            return file_content_b64, json.dumps(file_info)
            
        except Exception as e:
            logger.error(f"File transfer error: {e}", exc_info=True)
            return None, f"File transfer error: {e}"


class CommandHandler:
    """Handles server-side commands"""
    
    def __init__(self, client_manager: ClientManager, message_manager: MessageManager):
        self.client_manager = client_manager
        self.message_manager = message_manager
    
    async def handle_command(self, command: str, writer: asyncio.StreamWriter, client_name: str):
        """Handle a command from client"""
        try:
            parts = command.split(' ', 1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            if cmd == '/help':
                await self._cmd_help(writer)
            elif cmd == '/users':
                await self._cmd_users(writer)
            elif cmd == '/clear':
                await self._cmd_clear(writer)
            elif cmd == '/pm':
                await self._cmd_pm(writer, client_name, args)
            else:
                writer.write(f"Unknown command: {cmd}".encode('utf-8'))
                await writer.drain()
                
        except Exception as e:
            logger.error(f"Command handler error: {e}", exc_info=True)
            writer.write(f"Command error: {e}".encode('utf-8'))
            await writer.drain()
    
    async def _cmd_help(self, writer: asyncio.StreamWriter):
        """Handle /help command"""
        help_text = (
            "Available commands:\n"
            "/help - Show this help message\n"
            "/users - List all connected users\n"
            "/clear - Clear your chat history\n"
            "/pm <username> <message> - Send private message\n"
            ";exit - Quit the client"
        )
        writer.write(help_text.encode('utf-8'))
        await writer.drain()
    
    async def _cmd_users(self, writer: asyncio.StreamWriter):
        """Handle /users command"""
        clients = await self.client_manager.get_all_clients()
        users_list = ", ".join([c.name for c in clients])
        msg = f"Connected users ({len(clients)}): {users_list}"
        writer.write(msg.encode('utf-8'))
        await writer.drain()
    
    async def _cmd_clear(self, writer: asyncio.StreamWriter):
        """Handle /clear command"""
        writer.write("__CLEAR__".encode('utf-8'))
        await writer.drain()
    
    async def _cmd_pm(self, writer: asyncio.StreamWriter, client_name: str, args: str):
        """Handle /pm command"""
        pm_parts = args.split(' ', 1)
        
        if len(pm_parts) < 2:
            writer.write("Usage: /pm <username> <message>".encode('utf-8'))
            await writer.drain()
            return
            
        target_name = pm_parts[0]
        pm_message = pm_parts[1]
        
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
            except Exception as e:
                logger.error(f"PM send error: {e}")
                writer.write(f"Failed to send PM to {target_name}".encode('utf-8'))
                await writer.drain()
        else:
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
        os.system("cls" if sys.platform == "win32" else "clear")
    
    def _display_banner(self):
        """Display banner"""
        print(BANNER)
        print('=====The Server side=====')
        
        display_messages = self.message_manager.get_display_messages()
        for line in display_messages:  
            print(line)
        
        sys.stdout.write(CURSOR_SHOW)
        sys.stdout.flush()
    
    def _get_port(self) -> int:
        """Get port from user"""
        try:
            port = int(input('Port: '))
            if 1 <= port <= 65535:
                return port
            print("Port must be between 1 and 65535")
            return 0
        except ValueError:
            print("Invalid port number.")
            return 0
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a client connection"""
        client_addr = writer.get_extra_info('peername')
        logger.info(f"New connection from {client_addr}")
        
        await self.message_manager.add_message(
            f"New connection from {client_addr}", 
            is_user_message=False
        )
        
        client_added = False
        client_name = "Unknown"
        
        try:
            # Authenticate with token
            token_data = await reader.read(Config.BUFFER_SIZE)
            
            if not token_data:
                logger.warning(f"No token from {client_addr}")
                return
                
            received_token = token_data.decode('utf-8').strip()
            
            if received_token != Config.EXPECTED_TOKEN:
                logger.warning(f"Invalid token from {client_addr}")
                error_msg = "Authentication error: invalid token"
                writer.write(error_msg.encode('utf-8'))
                await writer.drain()
                return
            
            logger.info(f"Token authenticated for {client_addr}")
            
            # Get username
            name_data = await reader.read(Config.BUFFER_SIZE)
            
            if not name_data:
                logger.warning(f"No username from {client_addr}")
                return
                
            client_name = name_data.decode('utf-8').strip()
            # Sanitize username
            client_name = ''.join(c for c in client_name if c.isalnum() or c in ' ._-' )[:30]
            
            if not client_name:
                client_name = "Anonymous"
            
            logger.info(f"Username: {client_name}")
            
            if sys.platform == "win32":
                try:
                    ctypes.windll.kernel32.SetConsoleTitleW(
                        f"O.L.E.G. messenger | Client: {client_name}"
                    )
                except Exception:
                    pass
            
            # Add client to manager
            await self.client_manager.add_client(reader, writer, client_name, client_addr)
            client_added = True
            
            current_count = await self.client_manager.get_client_count()
            await self.message_manager.add_message(
                f"{client_name} Connected. Total Clients: {current_count}", 
                is_user_message=False
            )
            logger.info(f"{client_name} connected ({current_count} total)")
            
            # Broadcast join message
            join_msg = f"*** {client_name} has joined the chat ***"
            await self._broadcast_message(join_msg, writer)

            # Main message loop
            while True:
                data = await reader.read(Config.BUFFER_SIZE)
                
                if not data:
                    logger.info(f"Client {client_name} disconnected")
                    break
                
                message = data.decode('utf-8').strip()
                
                if not message:
                    continue

                # Handle file transfer: __FILE__|filename|base64data
                if message.startswith('__FILE__|'):
                    file_data = message[9:]  # Remove '__FILE__|' prefix
                    file_content, result = await self.file_handler.handle_file_transfer(
                        file_data, client_name
                    )
                    
                    if result.startswith('{'):
                        # Success - broadcast file info
                        await self._broadcast_message(f"__FILE_INFO__|{result}", writer)
                        await self.message_manager.add_message(
                            f"{client_name} sent a file", 
                            is_user_message=True
                        )
                    else:
                        # Error - send to sender only
                        writer.write(f"__ERROR__|{result}".encode('utf-8'))
                        await writer.drain()
                    continue

                # Handle commands
                if message.startswith('/'):
                    if self.command_handler:
                        await self.command_handler.handle_command(message, writer, client_name)
                    continue
                
                # Regular message - broadcast to all
                timestamp = datetime.now().strftime("[%H:%M:%S]")
                formatted_message = f"{timestamp} {client_name}: {message}"
                
                await self.message_manager.add_message(formatted_message, is_user_message=True)
                logger.info(f"Broadcast: {formatted_message}")
                await self._broadcast_message(formatted_message, writer)

        except ConnectionResetError:
            logger.info(f"Connection reset by {client_name} ({client_addr})")
        except Exception as e:
            logger.error(f"Error handling client {client_addr}: {e}", exc_info=True)
        finally:
            if client_added:
                await self.client_manager.remove_client(writer)
                remaining = await self.client_manager.get_client_count()
                await self.message_manager.add_message(
                    f"{client_name} disconnected. Remaining: {remaining}", 
                    is_user_message=False
                )
                logger.info(f"{client_name} disconnected ({remaining} remaining)")
                
                leave_msg = f"*** {client_name} has left the chat ***"
                await self._broadcast_message(leave_msg, None)
                    
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                logger.error(f"Close error: {e}")
    
    async def _broadcast_message(self, message: str, exclude_writer: Optional[asyncio.StreamWriter] = None):
        """Broadcast message to all clients"""
        current_clients = await self.client_manager.get_all_clients()
        
        for client in current_clients:
            if client.writer != exclude_writer:
                try:
                    client.writer.write(message.encode('utf-8'))
                    await client.writer.drain()
                except Exception as e:
                    logger.warning(f"Failed to send to {client.name}: {e}")
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
                logger.error("Invalid port")
                return

            self.server = await asyncio.start_server(
                self._handle_client,
                '0.0.0.0',
                self.port
            )
            
            logger.info(f"Server started on port {self.port}")
            
            await self.message_manager.add_message(
                f"Server started on port: {self.port}", 
                is_user_message=False
            )
            await self.message_manager.add_message(
                "Waiting for connections...", 
                is_user_message=False
            )
            await self.message_manager.add_message(
                f"Max file size: {self.file_handler.format_file_size(Config.MAX_FILE_SIZE)}", 
                is_user_message=False
            )
            
            # Initialize command handler
            self.command_handler = CommandHandler(self.client_manager, self.message_manager)

            async with self.server:
                logger.info("Serving forever")
                await self.server.serve_forever()

        except OSError as e:
            logger.error(f"Failed to start server: {e}")
            print(f"Failed to start server: {e}")
            if e.errno == 98 or e.errno == 10048:  # Address already in use
                print("Hint: Try a different port or check if another instance is running")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            print(f"Error occurred: {e}")
        finally:
            logger.info("ChatServer.run() ended")
            await self.message_manager.save_history()


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