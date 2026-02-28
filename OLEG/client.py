import asyncio
import os
import ctypes
import sys
import shutil
import json
<<<<<<< Updated upstream

'''no_escape=ctypes.windll.kernel32.GetConsoleWindow()

if no_escape:
    hmenu = ctypes.windll.user32.GetSystemMenu(no_escape, False)
    if hmenu:
        ctypes.windll.user32.EnableMenuItem(hmenu, 0xF060, 1|2)'''

# Устанавливаем заголовок консоли
ctypes.windll.kernel32.SetConsoleTitleW("O.L.E.G. messanger - You")
os.system('cls||clear')
=======
import base64
import re
import threading
import queue
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    from tkinter import Tk, Label, Frame
    from tkinter import font as tkfont
    TKINTER_AVAILABLE = True
except ImportError as e:
    TKINTER_AVAILABLE = False
    print(f"Warning: tkinterdnd2 not installed. Drag & drop disabled. Error: {e}")
    print("Install with: pip install tkinterdnd2")

if sys.platform == "win32":
    import ctypes
    ctypes.windll.kernel32.SetConsoleTitleW("O.L.E.G. messenger - Client")
>>>>>>> Stashed changes

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('client_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('CLIENT')

BANNER = '''#####   #       #####   #####
#   #   #       #       #    
#   #   #       ####    #  ##
#   #   #       #       #   #
#####   #####   #####   #####'''

CURSOR_HIDE = '\033[?25l'
CURSOR_SHOW = '\033[?25h'
CURSOR_HOME = '\033[H'
CLEAR_LINE = '\033[2K'


class Config:
    """Configuration constants"""
    MAX_MESSAGE_HISTORY = 1000
    MAX_CHAT_HISTORY = 500
    HISTORY_FILE = "chat_history.json"
    DOWNLOADS_FOLDER = "downloads"
    MAX_FILE_SIZE = 10 * 1024 * 1024
    TOKEN = "Y2010M07D23.01"
    AUTH_FILE = "auth.txt"
    BUFFER_SIZE = 1048576  # 1MB


class MessageManager:
    """Manages chat messages and history"""
    
    def __init__(self):
        logger.debug("MessageManager initialized")
        self.text_to_write: List[str] = []
        self.chat_history: List[str] = []
        self.current_input_line = ""
        self.lock = threading.Lock()
    
    def save_history(self):
        """Save chat history to file"""
        logger.debug("MessageManager.save_history() called")
        try:
            with self.lock:
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
    
    def load_history(self):
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
    
    def add_message(self, message: str, is_user_message: bool = False):
        """Add a message to display and optionally to history"""
        logger.debug(f"MessageManager.add_message() - Message: '{message[:50]}...', is_user: {is_user_message}")
        with self.lock:
            timestamp = datetime.now().strftime("[%H:%M:%S]")
            formatted_message = f"{timestamp} {message}"
            self.text_to_write.append(formatted_message)
            
            if is_user_message:
                self.chat_history.append(formatted_message)
                if len(self.chat_history) > Config.MAX_CHAT_HISTORY:
                    self.chat_history = self.chat_history[-Config.MAX_CHAT_HISTORY:]
                self.save_history()
                logger.debug(f"MessageManager.add_message() - Added to history (total: {len(self.chat_history)})")
            
            if len(self.text_to_write) > Config.MAX_MESSAGE_HISTORY:
                self.text_to_write = self.text_to_write[-Config.MAX_MESSAGE_HISTORY:]
                logger.debug(f"MessageManager.add_message() - Trimmed display messages")
    
    def get_display_messages(self) -> List[str]:
        """Get messages for display"""
        with self.lock:
            return self.text_to_write[-Config.MAX_MESSAGE_HISTORY:]
    
    def clear_messages(self):
        """Clear all messages"""
        logger.debug("MessageManager.clear_messages() called")
        with self.lock:
            self.text_to_write = []


class FileHandler:
    """Handles file operations"""
    
    def __init__(self):
        logger.debug("FileHandler initialized")
        os.makedirs(Config.DOWNLOADS_FOLDER, exist_ok=True)
    
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
    def detect_file_paths(text: str) -> List[str]:
        """Detect file paths in text"""
        logger.debug(f"FileHandler.detect_file_paths() - Text: '{text[:100]}...'")
        win_pattern = r'[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*'
        unix_pattern = r'/(?:[^/\0]+/)*[^/\0]*'
        
        paths = []
        paths.extend(re.findall(win_pattern, text))
        paths.extend(re.findall(unix_pattern, text))
        
        valid_paths = [p for p in paths if os.path.isfile(p)]
        logger.debug(f"FileHandler.detect_file_paths() - Found {len(valid_paths)} valid paths: {valid_paths}")
        return valid_paths
    
    async def send_file(self, writer: asyncio.StreamWriter, filepath: str, file_type: str = 'file', 
                       message_manager: MessageManager = None):
        """Send a file to server"""
        logger.info(f"FileHandler.send_file() - File: {filepath}, Type: {file_type}")
        try:
            if not os.path.exists(filepath):
                logger.error(f"FileHandler.send_file() - File not found: {filepath}")
                if message_manager:
                    message_manager.add_message(f"[Error] File not found: {filepath}", is_user_message=False)
                return False
            
            file_size = os.path.getsize(filepath)
            logger.debug(f"FileHandler.send_file() - File size: {file_size} bytes")
            
            if file_size > Config.MAX_FILE_SIZE:
                logger.error(f"FileHandler.send_file() - File too large: {file_size} > {Config.MAX_FILE_SIZE}")
                if message_manager:
                    message_manager.add_message(
                        f"[Error] File too large! Max: {self.format_file_size(Config.MAX_FILE_SIZE)}", 
                        is_user_message=False
                    )
                return False
            
            filename = os.path.basename(filepath)
            logger.debug(f"FileHandler.send_file() - Filename: {filename}")
            
            with open(filepath, 'rb') as f:
                file_content = base64.b64encode(f.read()).decode('utf-8')
            logger.debug(f"FileHandler.send_file() - Encoded {len(file_content)} characters")
            
            file_data = f"__FILE__|{filename}|{file_content}"
            logger.debug(f"FileHandler.send_file() - Sending {len(file_data)} bytes")
            
            writer.write(file_data.encode('utf-8'))
            await writer.drain()
            logger.info(f"FileHandler.send_file() - File sent successfully")
            
            if message_manager:
                message_manager.add_message(
                    f"✓ Sending {file_type}: {filename} ({self.format_file_size(file_size)})", 
                    is_user_message=False
                )
            return True
            
        except Exception as e:
            logger.error(f"FileHandler.send_file() - Error: {e}", exc_info=True)
            if message_manager:
                message_manager.add_message(f"[Error] Failed to send file: {e}", is_user_message=False)
            return False
    
    async def send_multiple_files(self, writer: asyncio.StreamWriter, filepaths: List[str],
                                  message_manager: MessageManager = None):
        """Send multiple files"""
        logger.info(f"FileHandler.send_multiple_files() - Files: {len(filepaths)}")
        for i, filepath in enumerate(filepaths, 1):
            logger.debug(f"FileHandler.send_multiple_files() - Sending {i}/{len(filepaths)}: {filepath}")
            if message_manager:
                message_manager.add_message(
                    f"Sending file {i}/{len(filepaths)}: {os.path.basename(filepath)}", 
                    is_user_message=False
                )
            await self.send_file(writer, filepath, message_manager=message_manager)
            await asyncio.sleep(0.5)


class DragDropWindow:
    """Manages drag & drop window"""
    
    def __init__(self, writer: asyncio.StreamWriter, file_handler: FileHandler, 
                 message_manager: MessageManager):
        logger.debug("DragDropWindow initialized")
        self.writer = writer
        self.file_handler = file_handler
        self.message_manager = message_manager
        self.window = None
        self.message_queue = queue.Queue()
        self.is_open = False
    
    def create_window(self):
        """Create drag & drop window in separate thread"""
        logger.info("DragDropWindow.create_window() called")
        
        if not TKINTER_AVAILABLE:
            logger.error("DragDropWindow.create_window() - tkinterdnd2 not available")
            self.message_manager.add_message(
                "[Error] tkinterdnd2 not installed. Install with: pip install tkinterdnd2", 
                is_user_message=False
            )
            return
        
        def create_window_thread():
            logger.debug("DragDropWindow.create_window_thread() started")
            try:
                if sys.platform == "win32":
                    try:
                        import comtypes
                        comtypes.CoInitialize()
                        logger.debug("DragDropWindow - COM initialized")
                    except Exception as e:
                        logger.warning(f"DragDropWindow - COM init failed: {e}")
                
                self.window = TkinterDnD.Tk()
                self.window.title("O.L.E.G. Drag & Drop")
                self.window.geometry("450x250")
                self.window.attributes('-topmost', True)
                self.window.resizable(False, False)
                self.is_open = True
                logger.debug("DragDropWindow - Window created")
                
                self._setup_ui()
                
                self.window.protocol("WM_DELETE_WINDOW", self._on_close)
                self.window.mainloop()
                logger.debug("DragDropWindow - Mainloop ended")
                
            except Exception as e:
                logger.error(f"DragDropWindow.create_window_thread() - Error: {e}", exc_info=True)
                self.is_open = False
        
        thread = threading.Thread(target=create_window_thread, daemon=True)
        thread.start()
        logger.info("DragDropWindow.create_window() - Thread started")
    
    def _setup_ui(self):
        """Setup UI components"""
        logger.debug("DragDropWindow._setup_ui() called")
        
        main_frame = Frame(self.window, bg='#2b2b2b', padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        title_label = Label(
            main_frame,
            text="📁 Drag & Drop Files Here",
            font=tkfont.Font(family="Arial", size=14, weight="bold"),
            bg='#2b2b2b',
            fg='#ffffff'
        )
        title_label.pack(pady=(0, 10))
        
        instr_label = Label(
            main_frame,
            text="Drop files from your file explorer\nThey will be sent automatically",
            font=tkfont.Font(family="Arial", size=10),
            bg='#2b2b2b',
            fg='#aaaaaa'
        )
        instr_label.pack(pady=(0, 20))
        
        self.drop_zone = Label(
            main_frame,
            text="⬇️ DROP FILES HERE ⬇️",
            font=tkfont.Font(family="Arial", size=12, weight="bold"),
            bg='#1a1a1a',
            fg='#00ff00',
            padx=40,
            pady=40,
            relief='solid',
            bd=2
        )
        self.drop_zone.pack(fill='x', pady=(0, 10))
        
        self.status_label = Label(
            main_frame,
            text="Ready - Waiting for files...",
            font=tkfont.Font(family="Arial", size=9),
            bg='#2b2b2b',
            fg='#888888'
        )
        self.status_label.pack(pady=(10, 0))
        
        self._setup_bindings()
        logger.debug("DragDropWindow._setup_ui() - UI setup complete")
    
    def _setup_bindings(self):
        """Setup drag & drop bindings"""
        logger.debug("DragDropWindow._setup_bindings() called")
        
        self.drop_zone.drop_target_register(DND_FILES)
        self.drop_zone.dnd_bind('<<Drop>>', self._on_drop)
        self.drop_zone.dnd_bind('<<DragEnter>>', self._on_drag_enter)
        self.drop_zone.dnd_bind('<<DragLeave>>', self._on_drag_leave)
        logger.debug("DragDropWindow._setup_bindings() - Bindings setup complete")
    
    def _on_drop(self, event):
        """Handle file drop"""
        logger.debug(f"DragDropWindow._on_drop() - Event data: {event.data[:100] if event.data else 'None'}")
        try:
            files = self.window.splitlist(event.data)
            logger.debug(f"DragDropWindow._on_drop() - Split files: {files}")
            valid_files = [f for f in files if os.path.isfile(f)]
            logger.debug(f"DragDropWindow._on_drop() - Valid files: {valid_files}")
            
            if valid_files:
                self.status_label.config(text=f"Sending {len(valid_files)} file(s)...", fg='#00ff00')
                self.window.update()
                
                for filepath in valid_files:
                    logger.debug(f"DragDropWindow._on_drop() - Queuing file: {filepath}")
                    self.message_queue.put(('file', filepath))
                
                self.status_label.config(text=f"✓ {len(valid_files)} file(s) queued!", fg='#00ff00')
                logger.info(f"DragDropWindow._on_drop() - Queued {len(valid_files)} files")
            else:
                self.status_label.config(text="No valid files dropped", fg='#ffaa00')
                logger.warning("DragDropWindow._on_drop() - No valid files")
        except Exception as e:
            logger.error(f"DragDropWindow._on_drop() - Error: {e}", exc_info=True)
            self.status_label.config(text=f"✗ Error: {str(e)}", fg='#ff0000')
    
    def _on_drag_enter(self, event):
        """Handle drag enter"""
        logger.debug("DragDropWindow._on_drag_enter() called")
        self.drop_zone.config(bg='#00aa00', fg='#ffffff')
    
    def _on_drag_leave(self, event):
        """Handle drag leave"""
        logger.debug("DragDropWindow._on_drag_leave() called")
        self.drop_zone.config(bg='#1a1a1a', fg='#00ff00')
    
    def _on_close(self):
        """Handle window close"""
        logger.debug("DragDropWindow._on_close() called")
        self.is_open = False
        try:
            self.window.destroy()
        except Exception as e:
            logger.error(f"DragDropWindow._on_close() - Error destroying window: {e}")
        self.window = None
    
    def get_queued_files(self) -> List[tuple]:
        """Get queued files from message queue"""
        files = []
        while not self.message_queue.empty():
            try:
                item = self.message_queue.get_nowait()
                files.append(item)
                logger.debug(f"DragDropWindow.get_queued_files() - Got: {item}")
            except queue.Empty:
                break
        logger.debug(f"DragDropWindow.get_queued_files() - Returning {len(files)} files")
        return files


class CommandHandler:
    """Handles client commands"""
    
    def __init__(self, file_handler: FileHandler, message_manager: MessageManager,
                 drag_drop_window: DragDropWindow = None):
        logger.debug("CommandHandler initialized")
        self.file_handler = file_handler
        self.message_manager = message_manager
        self.drag_drop_window = drag_drop_window
    
    def set_drag_drop_window(self, window: DragDropWindow):
        """Set drag drop window reference"""
        logger.debug("CommandHandler.set_drag_drop_window() called")
        self.drag_drop_window = window
    
    async def handle_command(self, message: str, writer: asyncio.StreamWriter) -> bool:
        """
        Handle a command message
        Returns True if message was a command, False otherwise
        """
        logger.debug(f"CommandHandler.handle_command() - Message: '{message}'")
        
        if not message:
            logger.debug("CommandHandler.handle_command() - Empty message")
            return False
        
        # Check for exit command first
        if message.lower() == ';exit':
            logger.info("CommandHandler.handle_command() - Exit command detected")
            return True
        
        # Check for command prefix
        if message.startswith('/'):
            parts = message.split(' ', 1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            logger.debug(f"CommandHandler.handle_command() - Command: {cmd}, Args: {args}")
            
            if cmd == '/help':
                await self._cmd_help(writer)
                return True
            
            elif cmd == '/file':
                await self._cmd_file(writer, args)
                return True
            
            elif cmd == '/img':
                await self._cmd_img(writer, args)
                return True
            
            elif cmd == '/drop':
                await self._cmd_drop()
                return True
            
            else:
                logger.warning(f"CommandHandler.handle_command() - Unknown command: {cmd}")
                self.message_manager.add_message(f"[Error] Unknown command: {cmd}", is_user_message=False)
                return True
        
        # Check for file paths in message
        paths = self.file_handler.detect_file_paths(message)
        if paths:
            logger.debug(f"CommandHandler.handle_command() - Detected {len(paths)} file paths")
            self.message_manager.add_message(f"Detected {len(paths)} file path(s)", is_user_message=False)
            self.message_manager.add_message("Send as files? Type 'yes' to confirm", is_user_message=False)
            return False  # Not a command, needs confirmation
        
        logger.debug("CommandHandler.handle_command() - Not a command")
        return False
    
    async def _cmd_help(self, writer: asyncio.StreamWriter):
        """Handle /help command"""
        logger.debug("CommandHandler._cmd_help() called")
        help_text = (
            "Available commands:\n"
            "/help - Show this help\n"
            "/file <path> - Send a file\n"
            "/img <path> - Send an image\n"
            "/drop - Open drag & drop window\n"
            ";exit - Quit the client"
        )
        self.message_manager.add_message(help_text, is_user_message=False)
        logger.info("CommandHandler._cmd_help() - Help displayed")
    
    async def _cmd_file(self, writer: asyncio.StreamWriter, args: str):
        """Handle /file command"""
        logger.debug(f"CommandHandler._cmd_file() - Args: '{args}'")
        if not args:
            logger.error("CommandHandler._cmd_file() - No filepath provided")
            self.message_manager.add_message(
                "[Error] Usage: /file <filepath>", 
                is_user_message=False
            )
            return
        
        filepath = args.strip().strip('"').strip("'")
        logger.debug(f"CommandHandler._cmd_file() - Cleaned filepath: '{filepath}'")
        await self.file_handler.send_file(writer, filepath, 'file', self.message_manager)
    
    async def _cmd_img(self, writer: asyncio.StreamWriter, args: str):
        """Handle /img command"""
        logger.debug(f"CommandHandler._cmd_img() - Args: '{args}'")
        if not args:
            logger.error("CommandHandler._cmd_img() - No filepath provided")
            self.message_manager.add_message(
                "[Error] Usage: /img <filepath>", 
                is_user_message=False
            )
            return
        
        filepath = args.strip().strip('"').strip("'")
        logger.debug(f"CommandHandler._cmd_img() - Cleaned filepath: '{filepath}'")
        await self.file_handler.send_file(writer, filepath, 'image', self.message_manager)
    
    async def _cmd_drop(self):
        """Handle /drop command"""
        logger.debug("CommandHandler._cmd_drop() called")
        if not TKINTER_AVAILABLE:
            logger.error("CommandHandler._cmd_drop() - tkinterdnd2 not available")
            self.message_manager.add_message(
                "[Error] tkinterdnd2 not installed. Install with: pip install tkinterdnd2", 
                is_user_message=False
            )
            return
        
        if self.drag_drop_window is None:
            logger.info("CommandHandler._cmd_drop() - Creating new drag drop window")
            self.message_manager.add_message("Opening drag & drop window...", is_user_message=False)
            # Will be created by main client
        elif not self.drag_drop_window.is_open:
            logger.info("CommandHandler._cmd_drop() - Reopening drag drop window")
            self.message_manager.add_message("Opening drag & drop window...", is_user_message=False)
        else:
            logger.warning("CommandHandler._cmd_drop() - Window already open")
            self.message_manager.add_message("Drag & drop window already open", is_user_message=False)


class ChatClient:
    """Main client class"""
    
    def __init__(self):
        logger.info("ChatClient initialized")
        self.message_manager = MessageManager()
        self.file_handler = FileHandler()
        self.drag_drop_window: Optional[DragDropWindow] = None
        self.command_handler: Optional[CommandHandler] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.shutdown_event = asyncio.Event()
        self.name = ""
        self.ip = ""
        self.port = 0
    
    def _load_auth(self) -> str:
        """Load saved username"""
        logger.debug("ChatClient._load_auth() called")
        try:
            if os.path.exists(Config.AUTH_FILE):
                with open(Config.AUTH_FILE, 'r') as f:
                    name = f.read().strip()
                    logger.debug(f"ChatClient._load_auth() - Loaded name: {name}")
                    return name
        except Exception as e:
            logger.error(f"ChatClient._load_auth() - Error: {e}")
        return ""
    
    def _save_auth(self, name: str):
        """Save username"""
        logger.debug(f"ChatClient._save_auth() - Name: {name}")
        try:
            with open(Config.AUTH_FILE, 'w') as f:
                f.write(name)
            logger.debug("ChatClient._save_auth() - Saved successfully")
        except Exception as e:
            logger.error(f"ChatClient._save_auth() - Error: {e}")
    
    def _get_connection_info(self):
        """Get connection information from user"""
        logger.debug("ChatClient._get_connection_info() called")
        try:
            self.ip = input("Enter the IP address: ").strip()
            logger.debug(f"ChatClient._get_connection_info() - IP: {self.ip}")
            
            self.port = int(input("Enter the port: ").strip())
            logger.debug(f"ChatClient._get_connection_info() - Port: {self.port}")
            
            saved_name = self._load_auth()
            if not saved_name:
                self.name = input("Enter your name: ").strip()
                self._save_auth(self.name)
                logger.debug(f"ChatClient._get_connection_info() - New name: {self.name}")
            else:
                self.name = saved_name
                print(f"Using saved name: {self.name}")
                logger.debug(f"ChatClient._get_connection_info() - Saved name: {self.name}")
        except Exception as e:
            logger.error(f"ChatClient._get_connection_info() - Error: {e}", exc_info=True)
            self.name = input("Enter your name: ").strip()
    
    def _clear_screen(self):
        """Clear console screen"""
        logger.debug("ChatClient._clear_screen() called")
        os.system("cls" if sys.platform == "win32" else "clear")
    
    def _display_banner(self):
        """Display banner and info"""
        logger.debug("ChatClient._display_banner() called")
        print(BANNER)
        print('=====The Client side=====')
        
        if not TKINTER_AVAILABLE:
            print("Note: Drag & drop disabled (tkinterdnd2 not installed)")
        
        display_messages = self.message_manager.get_display_messages()
        for line in display_messages:
            print(line)
        
        print(f"> {self.message_manager.current_input_line}", end='', flush=True)
        sys.stdout.write(CURSOR_SHOW)
        sys.stdout.flush()
    
    async def _connect(self) -> bool:
        """Connect to server"""
        logger.info(f"ChatClient._connect() - Connecting to {self.ip}:{self.port}")
        try:
            while True:
                try:
                    self.reader, self.writer = await asyncio.open_connection(self.ip, self.port)
                    logger.info("ChatClient._connect() - TCP connection established")
                    
                    self.writer.write(Config.TOKEN.encode('utf-8'))
                    await self.writer.drain()
                    logger.debug("ChatClient._connect() - Token sent")
                    break
                    
                except ConnectionRefusedError:
                    logger.warning("ChatClient._connect() - Connection refused, retrying...")
                    print("Connection refused, retrying...")
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"ChatClient._connect() - Connection error: {e}")
                    print(f"Connection error: {e}")
                    await asyncio.sleep(1)
            
            self.writer.write(self.name.encode('utf-8'))
            await self.writer.drain()
            logger.info(f"ChatClient._connect() - Username '{self.name}' sent")
            
            return True
            
        except Exception as e:
            logger.error(f"ChatClient._connect() - Failed: {e}", exc_info=True)
            return False
    
    async def _receive_messages(self):
        """Receive messages from server"""
        logger.info("ChatClient._receive_messages() started")
        try:
            while not self.shutdown_event.is_set():
                try:
                    data = await self.reader.read(Config.BUFFER_SIZE)
                    logger.debug(f"ChatClient._receive_messages() - Received {len(data)} bytes")
                    
                    if not data:
                        logger.info("ChatClient._receive_messages() - Connection closed by server")
                        self.message_manager.add_message("Connection closed by server", is_user_message=False)
                        break

                    message = data.decode('utf-8')
                    logger.debug(f"ChatClient._receive_messages() - Message: '{message[:100]}...'")
                    
                    if message == "__CLEAR__":
                        logger.debug("ChatClient._receive_messages() - Clear command received")
                        self.message_manager.clear_messages()
                        self._display_banner()
                        continue
                    
                    if message.startswith('__FILE_INFO__|'):
                        logger.debug("ChatClient._receive_messages() - File info received")
                        try:
                            file_info = json.loads(message[14:])
                            filename = file_info.get('original_name', 'unknown')
                            size = file_info.get('size', 'Unknown')
                            file_type = file_info.get('file_type', 'other')
                            sender = file_info.get('sender', 'Unknown')
                            
                            icons = {'images': '🖼️', 'documents': '📄', 'archives': '📦'}
                            icon = icons.get(file_type, '📎')
                            
                            file_msg = f"{icon} {sender} sent: {filename} ({size})"
                            self.message_manager.add_message(file_msg, is_user_message=False)
                            logger.info(f"ChatClient._receive_messages() - File from {sender}: {filename}")
                            
                        except Exception as e:
                            logger.error(f"ChatClient._receive_messages() - Parse error: {e}")
                            self.message_manager.add_message(f"Failed to parse file info: {e}", is_user_message=False)
                        continue
                    
                    if message.startswith('__ERROR__|'):
                        error_msg = message[10:]
                        logger.error(f"ChatClient._receive_messages() - Server error: {error_msg}")
                        self.message_manager.add_message(f"[Error] {error_msg}", is_user_message=False)
                        continue
                    
                    self.message_manager.add_message(message, is_user_message=False)

                except (ConnectionResetError, asyncio.CancelledError):
                    logger.warning("ChatClient._receive_messages() - Connection reset")
                    self.message_manager.add_message("Connection reset by server", is_user_message=False)
                    break
                except Exception as e:
                    logger.error(f"ChatClient._receive_messages() - Error: {e}", exc_info=True)
                    self.message_manager.add_message(f"[Error] {e}", is_user_message=False)
                    break
                    
        except Exception as e:
            logger.error(f"ChatClient._receive_messages() - Fatal error: {e}", exc_info=True)
        finally:
            logger.info("ChatClient._receive_messages() ended")
    
    async def _send_messages(self):
        """Send messages to server"""
        logger.info("ChatClient._send_messages() started")
        try:
            # Initialize command handler
            self.command_handler = CommandHandler(
                self.file_handler, 
                self.message_manager, 
                self.drag_drop_window
            )
            
            while not self.shutdown_event.is_set():
                # Check for drag-drop files
                if self.drag_drop_window:
                    files = self.drag_drop_window.get_queued_files()
                    for msg_type, filepath in files:
                        logger.debug(f"ChatClient._send_messages() - Processing queued file: {filepath}")
                        await self.file_handler.send_file(self.writer, filepath, message_manager=self.message_manager)
                
                sys.stdout.write(f"\r{CLEAR_LINE}")
                sys.stdout.flush()
                
                try:
                    loop = asyncio.get_event_loop()
                    message = await loop.run_in_executor(None, input, "")
                    logger.debug(f"ChatClient._send_messages() - User input: '{message}'")
                except EOFError:
                    logger.warning("ChatClient._send_messages() - EOF received")
                    break
                
                self.message_manager.current_input_line = message
                
                if message:
                    # Check if it's a command
                    is_command = await self.command_handler.handle_command(message, self.writer)
                    
                    if not is_command:
                        # Regular message - save to history
                        timestamp = datetime.now().strftime("[%H:%M:%S]")
                        formatted_msg = f"{timestamp} > You: {message}"
                        self.message_manager.add_message(formatted_msg, is_user_message=True)
                        logger.debug(f"ChatClient._send_messages() - Regular message added to history")
                    
                    # Send to server
                    if message.lower() != ';exit':
                        self.writer.write(message.encode('utf-8'))
                        await self.writer.drain()
                        logger.debug(f"ChatClient._send_messages() - Message sent to server")
                    
                    if message.lower() == ';exit':
                        logger.info("ChatClient._send_messages() - Exit requested")
                        break

                self.message_manager.current_input_line = ""
                self._display_banner()

        except Exception as e:
            logger.error(f"ChatClient._send_messages() - Error: {e}", exc_info=True)
            self.message_manager.add_message(f"[Error] {e}", is_user_message=False)
        finally:
            logger.info("ChatClient._send_messages() ended")
            self.shutdown_event.set()
            try:
                if self.writer:
                    self.writer.close()
                    await self.writer.wait_closed()
                    logger.debug("ChatClient._send_messages() - Writer closed")
            except Exception as e:
                logger.error(f"ChatClient._send_messages() - Close error: {e}")
    
    async def run(self):
        """Run the client"""
        logger.info("ChatClient.run() started")
        try:
            self._clear_screen()
            self._display_banner()
            
            self.message_manager.load_history()
            
            self._get_connection_info()
            
            # Add connection info to display
            self.message_manager.add_message(f"Target IP: {self.ip}", is_user_message=False)
            self.message_manager.add_message(f"Target Port: {self.port}", is_user_message=False)
            self.message_manager.add_message(f"Username: {self.name}", is_user_message=False)
            
            if not await self._connect():
                logger.error("ChatClient.run() - Connection failed")
                print("Unable to connect to the server")
                return
            
            self._clear_screen()
            self.message_manager.add_message("Connected to server.", is_user_message=False)
            self.message_manager.add_message("Type /help for commands, ;exit to quit", is_user_message=False)
            self.message_manager.add_message(
                f"Files save to: {os.path.abspath(Config.DOWNLOADS_FOLDER)}", 
                is_user_message=False
            )
            if TKINTER_AVAILABLE:
                self.message_manager.add_message("Type /drop to open drag & drop window", is_user_message=False)
            
            # Create drag drop window reference
            self.drag_drop_window = DragDropWindow(
                self.writer, 
                self.file_handler, 
                self.message_manager
            )
            self.command_handler = CommandHandler(
                self.file_handler, 
                self.message_manager, 
                self.drag_drop_window
            )
            
            # Start tasks
            receive_task = asyncio.create_task(self._receive_messages())
            logger.debug("ChatClient.run() - Receive task created")
            
            await self._send_messages()
            logger.debug("ChatClient.run() - Send messages completed")

            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                logger.debug("ChatClient.run() - Receive task cancelled")

        except Exception as e:
            logger.error(f"ChatClient.run() - Fatal error: {e}", exc_info=True)
            print(f"Error occurred: {e}")
        finally:
            self.shutdown_event.set()
            logger.info("ChatClient.run() - Saving history")
            self.message_manager.save_history()
            print("\nGoodbye")
            logger.info("ChatClient.run() ended")


async def main():
    """Main entry point"""
    logger.info("=" * 50)
    logger.info("CLIENT STARTING")
    logger.info("=" * 50)
    
<<<<<<< Updated upstream
    # Initial display
    print(BANNER)
    print('=====The Client side=====')
    
    # Get connection details
    auth_file = open('auth.txt', 'r')
    ip = input("Enter the IP address: ")
    port = int(input("Enter the port: "))
    try:
        if auth_file.read() == '':
            auth_file.close()
            auth_file = open('auth.txt', 'w')
            name = input("Enter your name: ")
            auth_file.write(name)
        else:
            name = auth_file.read()
    except Exception as e:
        print(f'Authorization error occured{e}')
        name = input("Enter your name: ")
    token = "Y2010M07D23.01"
    
    text_to_write.append("Enter the IP address: " + ip)
    text_to_write.append("Enter the port: " + str(port))
    text_to_write.append("Enter your name: " + name)
    auth_file.close()
=======
    client = ChatClient()
    await client.run()
>>>>>>> Stashed changes
    
    logger.info("=" * 50)
    logger.info("CLIENT SHUTDOWN")
    logger.info("=" * 50)

<<<<<<< Updated upstream
    try:
        # Connect to server
        while True:
            try:
                reader, writer = await asyncio.open_connection(ip, port)
                writer.write(token.encode('utf-8'))
                await writer.drain()
                break
            except ConnectionRefusedError:
                await asyncio.sleep(1)
                continue
            except Exception as e:
                print(f"Connection error: {e}")
                await asyncio.sleep(1)
                
        writer.write(name.encode('utf-8'))
        await writer.drain()
        
        # Clear screen and show chat interface
        clear_cmd()

        receive_task = asyncio.create_task(receive_messages(reader))
        await send_messages(writer)

        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass

    except ConnectionRefusedError:
        print("Unable to connect to the server")
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        print("\nGoodbye")
=======
>>>>>>> Stashed changes

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Client interrupted by user")
        print("\nGoodbye")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\nFatal error: {e}")