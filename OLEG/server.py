#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
O.L.E.G. Messenger - Server
Compatible with GUI Client
"""

import asyncio
import os
import sys
import json
import base64
import logging
import ctypes
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

# Windows console setup
if sys.platform == "win32":
    try:
        ctypes.windll.kernel32.SetConsoleTitleW("O.L.E.G. messenger - Server")
    except Exception:
        pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('server_debug.log', encoding='utf-8', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SERVER')


# ============================================================================
# CONFIGURATION
# ============================================================================
class Config:
    """Server configuration"""
    # Auth
    EXPECTED_TOKEN = "Y2010M07D23.01"
    
    # Network
    BUFFER_SIZE = 1048576  # 1MB
    HOST = '0.0.0.0'
    
    # Files
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    UPLOADS_FOLDER = "server_uploads"
    
    # History
    HISTORY_FILE = "server_history.json"
    MAX_HISTORY = 1000
    
    # File types
    ALLOWED_EXTENSIONS = {
        'image': {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'},
        'document': {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.xls', '.xlsx'},
        'archive': {'.zip', '.rar', '.7z', '.tar', '.gz'},
        'code': {'.py', '.js', '.html', '.css', '.json', '.xml', '.md'},
        'other': set()
    }


# ============================================================================
# MESSAGE MANAGER
# ============================================================================
class MessageManager:
    """Manages server message history"""
    
    def __init__(self):
        self.messages: List[dict] = []
        self.lock = asyncio.Lock()
    
    async def add(self, text: str, msg_type: str = "system"):
        """Add message to history"""
        async with self.lock:
            msg = {
                "text": text,
                "type": msg_type,
                "timestamp": datetime.now().isoformat()
            }
            self.messages.append(msg)
            if len(self.messages) > Config.MAX_HISTORY:
                self.messages = self.messages[-Config.MAX_HISTORY:]
            await self._save()
    
    async def _save(self):
        """Save history to file"""
        try:
            with open(Config.HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
    
    async def load(self) -> List[dict]:
        """Load history from file"""
        try:
            if os.path.exists(Config.HISTORY_FILE):
                with open(Config.HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self.messages = json.load(f)
                logger.info(f"Loaded {len(self.messages)} messages from history")
                return self.messages
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
        return []
    
    async def clear(self):
        """Clear all messages"""
        async with self.lock:
            self.messages = []
            await self._save()


# ============================================================================
# CLIENT INFO
# ============================================================================
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


# ============================================================================
# CLIENT MANAGER
# ============================================================================
class ClientManager:
    """Manages all connected clients"""
    
    def __init__(self):
        self.clients: List[ClientInfo] = []
        self.lock = asyncio.Lock()
    
    async def add(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                  name: str, addr: tuple) -> ClientInfo:
        """Add a new client"""
        async with self.lock:
            client = ClientInfo(reader, writer, name, addr)
            self.clients.append(client)
            logger.info(f"Client added: {name} at {addr}")
            return client
    
    async def remove(self, writer: asyncio.StreamWriter) -> Optional[ClientInfo]:
        """Remove a client"""
        async with self.lock:
            for i, client in enumerate(self.clients):
                if client.writer == writer:
                    removed = self.clients.pop(i)
                    logger.info(f"Client removed: {removed.name}")
                    return removed
            return None
    
    async def get_all(self) -> List[ClientInfo]:
        """Get all connected clients"""
        async with self.lock:
            return self.clients.copy()
    
    async def get_by_name(self, name: str) -> Optional[ClientInfo]:
        """Get client by name"""
        async with self.lock:
            for client in self.clients:
                if client.name.lower() == name.lower():
                    return client
            return None
    
    async def count(self) -> int:
        """Get number of connected clients"""
        async with self.lock:
            return len(self.clients)
    
    async def get_names(self) -> List[str]:
        """Get list of client names"""
        async with self.lock:
            return [c.name for c in self.clients]


# ============================================================================
# FILE HANDLER
# ============================================================================
class FileHandler:
    """Handles file operations on server"""
    
    def __init__(self):
        os.makedirs(Config.UPLOADS_FOLDER, exist_ok=True)
        logger.info(f"Uploads folder: {os.path.abspath(Config.UPLOADS_FOLDER)}")
    
    @staticmethod
    def format_size(size: int) -> str:
        """Human-readable file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    @staticmethod
    def sanitize_name(name: str) -> str:
        """Sanitize filename"""
        safe = ''.join(c for c in name if c.isalnum() or c in '._- ')
        return safe.strip()[:100] or "unnamed_file"
    
    @staticmethod
    def get_file_type(filename: str) -> str:
        """Determine file type by extension"""
        ext = Path(filename).suffix.lower()
        for ftype, exts in Config.ALLOWED_EXTENSIONS.items():
            if ext in exts:
                return ftype
        return 'other'
    
    async def process_file(self, file_data: str, sender_name: str) -> tuple:
        """
        Process incoming file
        Returns: (success: bool, file_info: dict or error_message: str)
        """
        try:
            # Parse: filename|base64content
            parts = file_data.split('|', 1)
            if len(parts) < 2:
                return False, "Invalid file format"
            
            filename = self.sanitize_name(parts[0])
            content_b64 = parts[1]
            
            if not filename:
                return False, "Invalid filename"
            
            # Decode base64
            try:
                decoded = base64.b64decode(content_b64)
            except Exception as e:
                return False, f"Base64 decode error: {e}"
            
            # Check size
            if len(decoded) > Config.MAX_FILE_SIZE:
                return False, f"File too large (max {self.format_size(Config.MAX_FILE_SIZE)})"
            
            # Save file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = f"{timestamp}_{filename}"
            file_path = os.path.join(Config.UPLOADS_FOLDER, safe_name)
            
            try:
                with open(file_path, 'wb') as f:
                    f.write(decoded)
                logger.info(f"File saved: {safe_name} ({self.format_size(len(decoded))})")
            except Exception as e:
                return False, f"Failed to save file: {e}"
            
            # Build file info for broadcast
            file_info = {
                'type': 'file',
                'filename': safe_name,
                'original_name': filename,
                'size': self.format_size(len(decoded)),
                'file_type': self.get_file_type(filename),
                'sender': sender_name,
                'timestamp': datetime.now().strftime("[%H:%M:%S]")
            }
            
            return True, file_info
            
        except Exception as e:
            logger.error(f"File process error: {e}", exc_info=True)
            return False, f"File error: {e}"


# ============================================================================
# COMMAND HANDLER
# ============================================================================
class CommandHandler:
    """Handles server-side commands"""
    
    def __init__(self, client_manager: ClientManager, message_manager: MessageManager,
                 broadcast_func):
        self.client_manager = client_manager
        self.message_manager = message_manager
        self.broadcast = broadcast_func
    
    async def handle(self, command: str, client: ClientInfo) -> bool:
        """
        Handle command from client
        Returns: True if command was handled, False otherwise
        """
        parts = command.split(' ', 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        logger.debug(f"Command from {client.name}: {cmd} {args}")
        
        try:
            if cmd == '/help':
                await self._cmd_help(client)
            elif cmd == '/users':
                await self._cmd_users(client)
            elif cmd == '/clear':
                await self._cmd_clear(client)
            elif cmd == '/pm':
                await self._cmd_pm(client, args)
            else:
                # Unknown command - let it pass as regular message
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Command handler error: {e}", exc_info=True)
            await self._send_error(client, f"Command error: {e}")
            return True
    
    async def _send_text(self, client: ClientInfo, text: str):
        """Send text to client"""
        try:
            client.writer.write(text.encode('utf-8') + b'\n')
            await client.writer.drain()
        except Exception as e:
            logger.error(f"Send to {client.name} failed: {e}")
    
    async def _send_error(self, client: ClientInfo, error: str):
        """Send error to client"""
        await self._send_text(client, f"__ERROR__|{error}")
    
    async def _cmd_help(self, client: ClientInfo):
        """Handle /help command"""
        help_text = (
            "📋 Available commands:\n"
            "/help - Show this help\n"
            "/users - List connected users\n"
            "/clear - Clear your chat\n"
            "/pm <user> <msg> - Private message"
        )
        await self._send_text(client, help_text)
    
    async def _cmd_users(self, client: ClientInfo):
        """Handle /users command"""
        names = await self.client_manager.get_names()
        count = len(names)
        msg = f"👥 Connected users ({count}): {', '.join(names) if names else 'None'}"
        await self._send_text(client, msg)
    
    async def _cmd_clear(self, client: ClientInfo):
        """Handle /clear command"""
        await self._send_text(client, "__CLEAR__")
        await self.message_manager.add(f"{client.name} cleared chat", "system")
    
    async def _cmd_pm(self, client: ClientInfo, args: str):
        """Handle /pm command"""
        pm_parts = args.split(' ', 1)
        
        if len(pm_parts) < 2:
            await self._send_error(client, "Usage: /pm <username> <message>")
            return
        
        target_name = pm_parts[0]
        pm_message = pm_parts[1]
        
        target = await self.client_manager.get_by_name(target_name)
        
        if target:
            # Send to target
            private_msg = f"[PM from {client.name}]: {pm_message}"
            await self._send_text(target, private_msg)
            
            # Confirm to sender
            await self._send_text(client, f"[PM to {target_name}]: {pm_message}")
            
            # Log
            await self.message_manager.add(f"{client.name} -> {target_name}: {pm_message}", "pm")
            logger.info(f"PM: {client.name} -> {target.name}")
        else:
            await self._send_error(client, f"User '{target_name}' not found")


# ============================================================================
# CHAT SERVER
# ============================================================================
class ChatServer:
    """Main server class"""
    
    def __init__(self):
        self.message_manager = MessageManager()
        self.client_manager = ClientManager()
        self.file_handler = FileHandler()
        self.command_handler: Optional[CommandHandler] = None
        self.server: Optional[asyncio.Server] = None
        self.port = 0
    
    def _print_banner(self):
        """Display server banner"""
        banner = (
            '#####   #       #####   #####\n'
            '#   #   #       #       #    \n'
            '#   #   #       ####    #  ##\n'
            '#   #   #       #       #   #\n'
            '#####   #####   #####   #####\n'
        )
        print(banner)
        print('=====The Server side=====')
        print(f'Token: {Config.EXPECTED_TOKEN}')
        print()
    
    async def _handle_client(self, reader: asyncio.StreamReader, 
                             writer: asyncio.StreamWriter):
        """Handle a client connection"""
        client_addr = writer.get_extra_info('peername')
        logger.info(f"New connection from {client_addr}")
        
        client = None
        client_name = "Unknown"
        
        try:
            # === Step 1: Authenticate with token ===
            token_line = await reader.readline()
            if not token_line:
                logger.warning(f"No token from {client_addr}")
                writer.close()
                return
            
            token = token_line.decode('utf-8').strip()
            
            if token != Config.EXPECTED_TOKEN:
                logger.warning(f"Invalid token from {client_addr}: {token}")
                writer.write(b"Authentication error: invalid token\n")
                await writer.drain()
                writer.close()
                return
            
            logger.info(f"Token authenticated: {client_addr}")
            
            # === Step 2: Get username ===
            name_line = await reader.readline()
            if not name_line:
                logger.warning(f"No username from {client_addr}")
                writer.close()
                return
            
            client_name = name_line.decode('utf-8').strip()
            # Sanitize username
            client_name = ''.join(c for c in client_name if c.isalnum() or c in ' ._-' )[:30]
            client_name = client_name or "Anonymous"
            
            # === Step 3: Register client ===
            client = await self.client_manager.add(reader, writer, client_name, client_addr)
            
            # Update console title
            if sys.platform == "win32":
                try:
                    ctypes.windll.kernel32.SetConsoleTitleW(
                        f"O.L.E.G. messenger | Clients: {await self.client_manager.count()}"
                    )
                except Exception:
                    pass
            
            # === Step 4: Broadcast join message ===
            join_msg = f"*** {client_name} has joined the chat ***"
            await self._broadcast(join_msg, exclude=client)
            await self.message_manager.add(join_msg, "system")
            logger.info(f"{client_name} connected ({await self.client_manager.count()} total)")
            
            # === Step 5: Main message loop ===
            while True:
                data = await reader.read(Config.BUFFER_SIZE)
                
                if not data:
                    logger.info(f"Client disconnected: {client_name}")
                    break
                
                message = data.decode('utf-8').strip()
                
                if not message:
                    continue
                
                logger.debug(f"From {client_name}: {message[:100]}")
                
                # Handle file transfer
                if message.startswith('__FILE__|'):
                    file_data = message[9:]  # Remove '__FILE__|' prefix
                    success, result = await self.file_handler.process_file(file_data, client_name)
                    
                    if success:
                        # Broadcast file info
                        file_info_json = json.dumps(result, ensure_ascii=False)
                        await self._broadcast(f"__FILE_INFO__|{file_info_json}")
                        await self.message_manager.add(f"{client_name} sent a file", "file")
                        logger.info(f"File from {client_name}: {result.get('original_name')}")
                    else:
                        # Send error to sender only
                        writer.write(f"__ERROR__|{result}\n".encode('utf-8'))
                        await writer.drain()
                    continue
                
                # Handle commands
                if message.startswith('/'):
                    handled = await self.command_handler.handle(message, client)
                    if handled:
                        continue
                
                # Regular message - broadcast to all
                timestamp = datetime.now().strftime("[%H:%M:%S]")
                formatted = f"{timestamp} {client_name}: {message}"
                
                await self.message_manager.add(formatted, "message")
                await self._broadcast(formatted)
                logger.info(f"Broadcast: {formatted}")
        
        except ConnectionResetError:
            logger.info(f"Connection reset: {client_name} ({client_addr})")
        except asyncio.CancelledError:
            logger.info(f"Connection cancelled: {client_name}")
        except Exception as e:
            logger.error(f"Error handling {client_addr}: {e}", exc_info=True)
        finally:
            # === Cleanup ===
            if client:
                await self.client_manager.remove(client.writer)
                
                remaining = await self.client_manager.count()
                leave_msg = f"*** {client_name} has left the chat ***"
                await self._broadcast(leave_msg)
                await self.message_manager.add(leave_msg, "system")
                
                logger.info(f"{client_name} disconnected ({remaining} remaining)")
                
                # Update console title
                if sys.platform == "win32":
                    try:
                        ctypes.windll.kernel32.SetConsoleTitleW(
                            f"O.L.E.G. messenger | Clients: {remaining}"
                        )
                    except Exception:
                        pass
            
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
    
    async def _broadcast(self, message: str, exclude: Optional[ClientInfo] = None):
        """Broadcast message to all clients"""
        clients = await self.client_manager.get_all()
        
        for client in clients:
            if exclude and client == exclude:
                continue
            
            try:
                client.writer.write(message.encode('utf-8') + b'\n')
                await client.writer.drain()
            except Exception as e:
                logger.warning(f"Failed to send to {client.name}: {e}")
                # Client will be removed on next read attempt
    
    async def run(self):
        """Run the server"""
        logger.info("Server starting...")
        
        self._print_banner()
        
        # Load history
        await self.message_manager.load()
        
        # Get port
        try:
            self.port = int(input('Enter port (default 8888): ').strip() or '8888')
            if not (1 <= self.port <= 65535):
                print("Invalid port. Using 8888.")
                self.port = 8888
        except ValueError:
            print("Invalid port. Using 8888.")
            self.port = 8888
        
        # Initialize command handler
        self.command_handler = CommandHandler(
            self.client_manager, 
            self.message_manager,
            self._broadcast
        )
        
        # Start server
        try:
            self.server = await asyncio.start_server(
                self._handle_client,
                Config.HOST,
                self.port
            )
            
            logger.info(f"Server started on {Config.HOST}:{self.port}")
            print(f"\n✅ Server running on port {self.port}")
            print(f"📁 Files saved to: {os.path.abspath(Config.UPLOADS_FOLDER)}")
            print(f"📝 History: {os.path.abspath(Config.HISTORY_FILE)}")
            print("\nWaiting for connections...\n")
            
            async with self.server:
                await self.server.serve_forever()
                
        except OSError as e:
            if e.errno in (98, 10048):  # Address already in use
                logger.error(f"Port {self.port} is already in use")
                print(f"\n❌ Error: Port {self.port} is already in use")
                print("Hint: Try a different port or close other instances")
            else:
                logger.error(f"Server error: {e}")
                print(f"\n❌ Server error: {e}")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            print(f"\n❌ Fatal error: {e}")
        finally:
            logger.info("Server shutdown")
            await self.message_manager.save()
            print("\nGoodbye!")


# ============================================================================
# ENTRY POINT
# ============================================================================
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
        print("\n⚠ Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")