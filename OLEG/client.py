#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
O.L.E.G. Messenger - Tkinter GUI Client
Async asyncio + tkinter with drag & drop support
"""

import asyncio
import os
import sys
import json
import base64
import logging
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Callable
from tkinter import (
    Tk, Frame, Text, Entry, Button, Label, Scrollbar, 
    Menu, filedialog, messagebox, font as tkfont, END, NORMAL, DISABLED
)
from tkinterdnd2 import DND_FILES, TkinterDnD

# Try to import aioconsole for async input fallback
try:
    from aioconsole import aprint, ainput
    AIOCONSOLE_AVAILABLE = True
except ImportError:
    AIOCONSOLE_AVAILABLE = False

# Windows console setup
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW("O.L.E.G. messenger - GUI Client")
        # Enable ANSI colors in console (for debug output)
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            mode.value |= 0x0004
            kernel32.SetConsoleMode(handle, mode)
    except Exception:
        pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('client_gui.log', encoding='utf-8', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('CLIENT_GUI')


# ============================================================================
# CONFIGURATION
# ============================================================================
class Config:
    """Application configuration"""
    # Network
    DEFAULT_TOKEN = "Y2010M07D23.01"
    BUFFER_SIZE = 1048576  # 1MB
    RECONNECT_DELAY = 1.0
    
    # UI
    APP_TITLE = "O.L.E.G. Messenger"
    CHAT_BG = "#1e1e1e"
    CHAT_FG = "#e0e0e0"
    INPUT_BG = "#2d2d2d"
    INPUT_FG = "#ffffff"
    ACCENT_COLOR = "#007acc"
    ACCENT_HOVER = "#0099cc"
    USER_MSG_BG = "#005a9e"
    OTHER_MSG_BG = "#333333"
    SYSTEM_MSG_COLOR = "#888888"
    ERROR_COLOR = "#ff6b6b"
    SUCCESS_COLOR = "#51cf66"
    
    # Files
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    DOWNLOADS_FOLDER = "downloads"
    HISTORY_FILE = "chat_history.json"
    AUTH_FILE = "auth.json"
    MAX_HISTORY = 1000
    
    # Fonts
    FONT_MAIN = ("Segoe UI", 10)
    FONT_BOLD = ("Segoe UI", 10, "bold")
    FONT_SMALL = ("Segoe UI", 9)
    FONT_MONO = ("Consolas", 9)


# ============================================================================
# MESSAGE MANAGER
# ============================================================================
class MessageManager:
    """Manages chat messages and persistence"""
    
    def __init__(self):
        self.messages: List[dict] = []
        self.lock = asyncio.Lock()
    
    async def add(self, text: str, sender: str = "system", 
                  msg_type: str = "text", timestamp: Optional[datetime] = None,
                  is_own: bool = False, file_info: Optional[dict] = None):
        """Add a message to history"""
        async with self.lock:
            msg = {
                "text": text,
                "sender": sender,
                "type": msg_type,
                "timestamp": (timestamp or datetime.now()).isoformat(),
                "is_own": is_own,
                "file_info": file_info
            }
            self.messages.append(msg)
            if len(self.messages) > Config.MAX_HISTORY:
                self.messages = self.messages[-Config.MAX_HISTORY:]
            await self._save()
    
    async def _save(self):
        """Save history to file"""
        try:
            with open(Config.HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.messages[-Config.MAX_HISTORY:], f, ensure_ascii=False, indent=2)
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
    
    def get_recent(self, count: int = 100) -> List[dict]:
        """Get recent messages"""
        return self.messages[-count:]


# ============================================================================
# FILE HANDLER
# ============================================================================
class FileHandler:
    """Handles file operations"""
    
    def __init__(self):
        os.makedirs(Config.DOWNLOADS_FOLDER, exist_ok=True)
    
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
        types = {
            'image': {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'},
            'document': {'.pdf', '.doc', '.docx', '.txt', '.rtf'},
            'archive': {'.zip', '.rar', '.7z', '.tar', '.gz'},
            'code': {'.py', '.js', '.html', '.css', '.json'},
        }
        for ftype, exts in types.items():
            if ext in exts:
                return ftype
        return 'file'
    
    async def encode_file(self, filepath: str) -> Optional[tuple]:
        """Encode file for sending: returns (filename, base64_content) or None"""
        try:
            if not os.path.isfile(filepath):
                return None
            
            size = os.path.getsize(filepath)
            if size > Config.MAX_FILE_SIZE:
                return None, f"File too large (max {self.format_size(Config.MAX_FILE_SIZE)})"
            
            filename = os.path.basename(filepath)
            with open(filepath, 'rb') as f:
                content = base64.b64encode(f.read()).decode('utf-8')
            
            return filename, content
        except Exception as e:
            logger.error(f"File encode error: {e}")
            return None, str(e)
    
    def save_file(self, filename: str, content_b64: str) -> Optional[str]:
        """Save received file, returns path or None"""
        try:
            safe_name = self.sanitize_name(filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_name = f"{timestamp}_{safe_name}"
            path = os.path.join(Config.DOWNLOADS_FOLDER, final_name)
            
            with open(path, 'wb') as f:
                f.write(base64.b64decode(content_b64))
            
            return path
        except Exception as e:
            logger.error(f"File save error: {e}")
            return None


# ============================================================================
# NETWORK CLIENT
# ============================================================================
class NetworkClient:
    """Asyncio network client for server communication"""
    
    def __init__(self, on_message: Callable, on_connect: Callable, 
                 on_disconnect: Callable, on_error: Callable):
        self.on_message = on_message
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_error = on_error
        
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected = False
        self.username = ""
        self.token = Config.DEFAULT_TOKEN
        self._receive_task: Optional[asyncio.Task] = None
    
    async def connect(self, host: str, port: int, username: str) -> bool:
        """Connect to server"""
        try:
            logger.info(f"Connecting to {host}:{port} as {username}")
            
            self.reader, self.writer = await asyncio.open_connection(host, port)
            
            # Send token
            self.writer.write(self.token.encode('utf-8') + b'\n')
            await self.writer.drain()
            
            # Check auth response
            response = await self.reader.readline()
            if response and b'error' in response.lower():
                await self.on_error(response.decode().strip())
                await self.disconnect()
                return False
            
            # Send username
            self.writer.write(username.encode('utf-8') + b'\n')
            await self.writer.drain()
            
            self.username = username
            self.connected = True
            
            # Start receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            await self.on_connect(username)
            logger.info(f"Connected as {username}")
            return True
            
        except ConnectionRefusedError:
            await self.on_error("Connection refused - is server running?")
        except OSError as e:
            await self.on_error(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Connect error: {e}", exc_info=True)
            await self.on_error(f"Connection failed: {e}")
        
        return False
    
    async def _receive_loop(self):
        """Receive messages from server"""
        try:
            while self.connected and self.reader:
                data = await self.reader.read(Config.BUFFER_SIZE)
                if not data:
                    break
                
                message = data.decode('utf-8').strip()
                await self._process_message(message)
                
        except asyncio.CancelledError:
            pass
        except ConnectionResetError:
            await self.on_disconnect("Connection reset by server")
        except Exception as e:
            logger.error(f"Receive error: {e}", exc_info=True)
            await self.on_error(f"Receive error: {e}")
        finally:
            self.connected = False
    
    async def _process_message(self, message: str):
        """Process incoming message"""
        if not message:
            return
        
        # File info
        if message.startswith('__FILE_INFO__|'):
            try:
                file_info = json.loads(message[14:])
                await self.on_message({
                    'type': 'file',
                    'sender': file_info.get('sender', 'Unknown'),
                    'filename': file_info.get('original_name', 'unknown'),
                    'size': file_info.get('size', '?'),
                    'file_type': file_info.get('file_type', 'other'),
                    'timestamp': file_info.get('timestamp', '')
                })
            except Exception as e:
                logger.error(f"File info parse error: {e}")
            return
        
        # File content (for download)
        if message.startswith('__FILE_DATA__|'):
            # Format: __FILE_DATA__|filename|base64content
            parts = message[14:].split('|', 1)
            if len(parts) >= 2:
                filename, content = parts[0], parts[1]
                # Save file and notify
                file_handler = FileHandler()
                saved_path = file_handler.save_file(filename, content)
                if saved_path:
                    await self.on_message({
                        'type': 'file_received',
                        'filename': filename,
                        'path': saved_path,
                        'size': Config.file_handler.format_size(len(content))
                    })
            return
        
        # System commands
        if message == "__CLEAR__":
            await self.on_message({'type': 'clear'})
            return
        
        if message.startswith('__ERROR__|'):
            await self.on_error(message[10:])
            return
        
        # Regular chat message
        # Format: [HH:MM:SS] Username: message
        await self.on_message({
            'type': 'text',
            'raw': message,
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })
    
    async def send(self, text: str):
        """Send text message to server"""
        if not self.connected or not self.writer:
            return False
        try:
            self.writer.write(text.encode('utf-8') + b'\n')
            await self.writer.drain()
            return True
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False
    
    async def send_file(self, filepath: str):
        """Send file to server"""
        if not self.connected or not self.writer:
            return False, "Not connected"
        
        file_handler = FileHandler()
        result = await file_handler.encode_file(filepath)
        
        if result is None:
            return False, "File not found"
        if isinstance(result, tuple) and result[1]:
            return False, result[1]
        
        filename, content = result
        file_type = file_handler.get_file_type(filename)
        
        # Send file marker
        file_msg = f"__FILE__|{filename}|{content}"
        return await self.send(file_msg), None
    
    async def disconnect(self):
        """Disconnect from server"""
        self.connected = False
        
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = None
        
        await self.on_disconnect("Disconnected")
        logger.info("Disconnected")


# ============================================================================
# MAIN GUI APPLICATION
# ============================================================================
class ChatApp:
    """Main Tkinter application"""
    
    def __init__(self, root: Tk):
        self.root = root
        self.root.title(Config.APP_TITLE)
        self.root.geometry("900x700")
        self.root.minsize(700, 500)
        self.root.configure(bg=Config.CHAT_BG)
        
        # State
        self.network: Optional[NetworkClient] = None
        self.message_manager = MessageManager()
        self.file_handler = FileHandler()
        self.connected = False
        self.username = ""
        self.server_host = ""
        self.server_port = 0
        
        # Async loop integration
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._async_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._async_thread.start()
        
        # Build UI
        self._setup_styles()
        self._build_ui()
        self._load_settings()
        
        # Schedule async tasks
        self.root.after(100, self._init_async)
    
    def _run_async_loop(self):
        """Run asyncio event loop in background thread"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def _safe_call_async(self, coro):
        """Safely schedule coroutine in async loop"""
        if not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(coro, self.loop)
    
    def _setup_styles(self):
        """Configure UI styles"""
        self.root.option_add('*Font', Config.FONT_MAIN)
        self.root.option_add('*Entry.Font', Config.FONT_MAIN)
        self.root.option_add('*Text.Font', Config.FONT_MAIN)
        
        # Configure text tags for message styling
        self.chat_tags = {
            'own': {'bg': Config.USER_MSG_BG, 'fg': '#fff', 'lmargin1': 200, 'lmargin2': 200},
            'other': {'bg': Config.OTHER_MSG_BG, 'fg': Config.CHAT_FG, 'lmargin1': 10, 'lmargin2': 10},
            'system': {'fg': Config.SYSTEM_MSG_COLOR, 'justify': 'center'},
            'error': {'fg': Config.ERROR_COLOR},
            'success': {'fg': Config.SUCCESS_COLOR},
            'timestamp': {'fg': '#888'},
            'username': {'fg': '#4da6ff', 'font': Config.FONT_BOLD},
        }
    
    def _build_ui(self):
        """Build the user interface"""
        # Main container
        main_frame = Frame(self.root, bg=Config.CHAT_BG)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # === Chat display area ===
        chat_frame = Frame(main_frame, bg=Config.CHAT_BG)
        chat_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        self.chat_display = Text(
            chat_frame,
            bg=Config.CHAT_BG,
            fg=Config.CHAT_FG,
            font=Config.FONT_MAIN,
            wrap='word',
            state=DISABLED,
            relief='flat',
            cursor='arrow',
            spacing1=4,
            spacing3=4
        )
        self.chat_display.pack(side='left', fill='both', expand=True)
        
        # Configure tags
        for tag_name, config in self.chat_tags.items():
            self.chat_display.tag_configure(tag_name, **config)
        
        # Scrollbar
        chat_scroll = Scrollbar(chat_frame, command=self.chat_display.yview)
        chat_scroll.pack(side='right', fill='y')
        self.chat_display.configure(yscrollcommand=chat_scroll.set)
        
        # Make links clickable
        self.chat_display.tag_bind('link', '<Button-1>', self._on_link_click)
        self.chat_display.tag_bind('link', '<Enter>', lambda e: self.chat_display.config(cursor='hand2'))
        self.chat_display.tag_bind('link', '<Leave>', lambda e: self.chat_display.config(cursor='arrow'))
        
        # === Input area ===
        input_frame = Frame(main_frame, bg=Config.INPUT_BG, padx=10, pady=10)
        input_frame.pack(fill='x', side='bottom')
        
        # Message entry
        self.message_entry = Entry(
            input_frame,
            bg=Config.INPUT_BG,
            fg=Config.INPUT_FG,
            insertbackground=Config.INPUT_FG,
            relief='flat',
            font=Config.FONT_MAIN
        )
        self.message_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.message_entry.bind('<Return>', self._on_message_send)
        self.message_entry.bind('<KeyRelease>', self._on_entry_key)
        
        # File button
        self.file_btn = Button(
            input_frame,
            text="📎",
            bg=Config.ACCENT_COLOR,
            fg='white',
            activebackground=Config.ACCENT_HOVER,
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            font=Config.FONT_BOLD,
            width=3,
            command=self._on_file_select
        )
        self.file_btn.pack(side='right', padx=(5, 0))
        
        # Send button
        self.send_btn = Button(
            input_frame,
            text="➤",
            bg=Config.ACCENT_COLOR,
            fg='white',
            activebackground=Config.ACCENT_HOVER,
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            font=Config.FONT_BOLD,
            width=3,
            command=self._on_message_send
        )
        self.send_btn.pack(side='right')
        
        # === Drag & drop area ===
        self._setup_drag_drop(input_frame)
        
        # === Connection bar ===
        self._build_connection_bar(main_frame)
        
        # === Context menu ===
        self._setup_context_menu()
        
        # Focus entry
        self.message_entry.focus_set()
    
    def _setup_drag_drop(self, parent):
        """Setup drag & drop on input frame"""
        parent.drop_target_register(DND_FILES)
        parent.dnd_bind('<<Drop>>', self._on_file_drop)
        parent.dnd_bind('<<DragEnter>>', self._on_drag_enter)
        parent.dnd_bind('<<DragLeave>>', self._on_drag_leave)
        
        # Visual indicator
        self.drop_indicator = Label(
            parent,
            text="📁 Drop files here",
            bg=Config.INPUT_BG,
            fg=Config.SYSTEM_MSG_COLOR,
            font=Config.FONT_SMALL
        )
        # Don't pack by default - show on drag enter
    
    def _on_drag_enter(self, event):
        """Visual feedback on drag enter"""
        self.drop_indicator.place(relx=0.5, rely=0.5, anchor='center')
        self.file_btn.config(bg=Config.SUCCESS_COLOR)
    
    def _on_drag_leave(self, event):
        """Remove visual feedback"""
        self.drop_indicator.place_forget()
        self.file_btn.config(bg=Config.ACCENT_COLOR)
    
    def _on_file_drop(self, event):
        """Handle dropped files"""
        self.drop_indicator.place_forget()
        self.file_btn.config(bg=Config.ACCENT_COLOR)
        
        files = self.root.splitlist(event.data)
        valid_files = [f for f in files if os.path.isfile(f)]
        
        for filepath in valid_files:
            self._safe_call_async(self._send_file_async(filepath))
    
    def _build_connection_bar(self, parent):
        """Build connection status bar"""
        conn_frame = Frame(parent, bg='#151515', height=30)
        conn_frame.pack(fill='x', side='top', pady=(0, 5))
        conn_frame.pack_propagate(False)
        
        # Status indicator
        self.status_dot = Label(conn_frame, text="●", fg=Config.ERROR_COLOR, 
                               bg='#151515', font=("Segoe UI", 14))
        self.status_dot.pack(side='left', padx=(10, 5))
        
        # Status text
        self.status_label = Label(conn_frame, text="Disconnected", 
                                 fg=Config.SYSTEM_MSG_COLOR, bg='#151515',
                                 font=Config.FONT_SMALL)
        self.status_label.pack(side='left')
        
        # Connect button
        self.connect_btn = Button(
            conn_frame,
            text="Connect",
            bg=Config.ACCENT_COLOR,
            fg='white',
            activebackground=Config.ACCENT_HOVER,
            relief='flat',
            cursor='hand2',
            font=Config.FONT_SMALL,
            command=self._show_connect_dialog,
            padx=15
        )
        self.connect_btn.pack(side='right', padx=10)
        
        # Settings button
        settings_btn = Button(
            conn_frame,
            text="⚙",
            bg='#151515',
            fg=Config.SYSTEM_MSG_COLOR,
            activeforeground=Config.ACCENT_COLOR,
            relief='flat',
            cursor='hand2',
            font=Config.FONT_BOLD,
            command=self._show_settings,
            width=2
        )
        settings_btn.pack(side='right')
    
    def _setup_context_menu(self):
        """Setup right-click context menu for chat"""
        self.context_menu = Menu(self.root, tearoff=0, bg=Config.OTHER_MSG_BG, 
                                fg=Config.CHAT_FG, activebackground=Config.ACCENT_COLOR,
                                activeforeground='white', relief='flat', borderwidth=1)
        self.context_menu.add_command(label="Copy", command=self._copy_selection)
        self.context_menu.add_command(label="Clear Chat", command=self._clear_chat)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Save Chat", command=self._save_chat)
        
        self.chat_display.bind('<Button-3>', self._show_context_menu)
    
    def _show_context_menu(self, event):
        """Show context menu at cursor"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================
    
    def _on_message_send(self, event=None):
        """Handle message send"""
        message = self.message_entry.get().strip()
        if not message or not self.connected:
            return
        
        self.message_entry.delete(0, END)
        
        # Handle local commands
        if message.startswith('/'):
            self._handle_local_command(message)
            return
        
        # Send to server
        self._safe_call_async(self.network.send(message))
        
        # Display locally
        self._add_message(message, sender=self.username, is_own=True)
    
    def _handle_local_command(self, cmd: str):
        """Handle client-side commands"""
        parts = cmd.split(' ', 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if command == '/help':
            self._show_help()
        elif command == '/clear':
            self._clear_chat()
        elif command == '/connect':
            self._parse_connect_command(args)
        elif command == '/disconnect':
            self._safe_call_async(self.network.disconnect())
        elif command == '/users':
            self._safe_call_async(self.network.send('/users'))
        elif command.startswith('/pm '):
            self._safe_call_async(self.network.send(cmd))
        else:
            self._add_message(f"Unknown command: {command}", msg_type='error')
    
    def _show_help(self):
        """Show help message"""
        help_text = (
            "📋 Available commands:\n"
            "/help - Show this help\n"
            "/clear - Clear chat\n"
            "/connect <host> <port> - Connect to server\n"
            "/disconnect - Disconnect\n"
            "/users - List connected users\n"
            "/pm <user> <msg> - Private message\n"
            "\n💡 Tip: Drag & drop files to send!"
        )
        self._add_message(help_text, msg_type='system')
    
    def _parse_connect_command(self, args: str):
        """Parse /connect command"""
        parts = args.split()
        if len(parts) >= 2:
            host, port = parts[0], parts[1]
            try:
                port = int(port)
                self._safe_call_async(self._connect_async(host, port))
            except ValueError:
                self._add_message("Invalid port number", msg_type='error')
        else:
            self._show_connect_dialog()
    
    def _on_file_select(self):
        """Open file dialog for sending"""
        filepath = filedialog.askopenfilename(title="Select file to send")
        if filepath:
            self._safe_call_async(self._send_file_async(filepath))
    
    def _on_entry_key(self, event):
        """Handle entry key events"""
        # Enable/disable send button based on input
        has_text = bool(self.message_entry.get().strip())
        self.send_btn.config(state='normal' if has_text and self.connected else 'disabled')
    
    def _on_link_click(self, event):
        """Handle clickable links in chat"""
        idx = self.chat_display.index(f"@{event.x},{event.y}")
        for tag in self.chat_display.tag_names(idx):
            if tag.startswith('link:'):
                url = tag[5:]  # Remove 'link:' prefix
                import webbrowser
                webbrowser.open(url)
                break
    
    def _copy_selection(self):
        """Copy selected text to clipboard"""
        try:
            text = self.chat_display.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except Exception:
            pass
    
    def _clear_chat(self):
        """Clear chat display"""
        self.chat_display.config(state=NORMAL)
        self.chat_display.delete('1.0', END)
        self.chat_display.config(state=DISABLED)
        self._safe_call_async(self.message_manager.clear())
        self._add_message("Chat cleared", msg_type='system')
    
    def _save_chat(self):
        """Save chat to file"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save chat history"
        )
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    for msg in self.message_manager.get_recent(500):
                        ts = msg['timestamp'][:19].replace('T', ' ')
                        sender = msg.get('sender', '')
                        text = msg.get('text', msg.get('raw', ''))
                        f.write(f"[{ts}] {sender}: {text}\n")
                self._add_message(f"Chat saved to {filepath}", msg_type='success')
            except Exception as e:
                self._add_message(f"Save error: {e}", msg_type='error')
    
    # ========================================================================
    # ASYNC OPERATIONS
    # ========================================================================
    
    def _init_async(self):
        """Initialize async components"""
        self.network = NetworkClient(
            on_message=self._on_server_message,
            on_connect=self._on_connected,
            on_disconnect=self._on_disconnected,
            on_error=self._on_error
        )
        
        # Load history and display
        async def load_and_display():
            history = await self.message_manager.load()
            for msg in history[-50:]:
                self._display_message(msg)
        
        self._safe_call_async(load_and_display())
        
        # Auto-connect if settings exist
        if self.server_host and self.server_port and self.username:
            self._safe_call_async(self._connect_async(self.server_host, self.server_port))
    
    async def _connect_async(self, host: str, port: int):
        """Async connect to server"""
        if not self.username:
            self._show_connect_dialog()
            return
        
        self._set_status("Connecting...", Config.SYSTEM_MSG_COLOR)
        
        success = await self.network.connect(host, port, self.username)
        
        if success:
            self._set_status(f"Connected to {host}:{port}", Config.SUCCESS_COLOR)
            self._add_message(f"✓ Connected to {host}:{port}", msg_type='success')
        else:
            self._set_status("Connection failed", Config.ERROR_COLOR)
    
    async def _send_file_async(self, filepath: str):
        """Async send file to server"""
        filename = os.path.basename(filepath)
        size = self.file_handler.format_size(os.path.getsize(filepath))
        
        self._add_message(f"📤 Sending: {filename} ({size})", msg_type='system')
        
        success, error = await self.network.send_file(filepath)
        
        if success:
            self._add_message(f"✓ Sent: {filename}", msg_type='success')
        else:
            self._add_message(f"✗ Failed: {error or 'Unknown error'}", msg_type='error')
    
    # ========================================================================
    # CALLBACKS FROM NETWORK
    # ========================================================================
    
    def _on_server_message(self, msg: dict):
        """Handle message from server (called from async context)"""
        # Schedule UI update in main thread
        self.root.after(0, lambda: self._handle_server_message(msg))
    
    def _handle_server_message(self, msg: dict):
        """Process server message in UI thread"""
        msg_type = msg.get('type')
        
        if msg_type == 'clear':
            self._clear_chat()
            return
        
        if msg_type == 'file':
            # File notification from another user
            sender = msg.get('sender', 'Unknown')
            filename = msg.get('filename', 'unknown')
            size = msg.get('size', '?')
            ftype = msg.get('file_type', 'file')
            
            icons = {'image': '🖼️', 'document': '📄', 'archive': '📦', 'code': '💻'}
            icon = icons.get(ftype, '📎')
            
            display = f"{icon} {sender} sent: {filename} ({size})"
            self._add_message(display, sender=sender, msg_type='file')
            return
        
        if msg_type == 'file_received':
            # Our file was saved
            path = msg.get('path')
            self._add_message(f"✓ File saved: {path}", msg_type='success')
            return
        
        # Regular text message
        raw = msg.get('raw', '')
        timestamp = msg.get('timestamp', '')
        
        # Parse: [HH:MM:SS] Username: message
        match = re.match(r'\[([\d:]+)\]\s+([^:]+):\s*(.+)', raw)
        if match:
            ts, sender, text = match.groups()
            is_own = sender.lower() == self.username.lower()
            self._add_message(text, sender=sender, timestamp=ts, is_own=is_own)
        else:
            self._add_message(raw, msg_type='system')
    
    def _on_connected(self, username: str):
        """Called when connected"""
        self.root.after(0, lambda: self._set_connected(True, username))
    
    def _on_disconnected(self, reason: str):
        """Called when disconnected"""
        self.root.after(0, lambda: self._set_connected(False, reason))
    
    def _on_error(self, error: str):
        """Called on error"""
        self.root.after(0, lambda: self._add_message(f"⚠ {error}", msg_type='error'))
    
    # ========================================================================
    # UI UPDATES
    # ========================================================================
    
    def _add_message(self, text: str, sender: str = "system", 
                     msg_type: str = "text", timestamp: Optional[str] = None,
                     is_own: bool = False, file_info: Optional[dict] = None):
        """Add message to chat display"""
        self.chat_display.config(state=NORMAL)
        
        ts = timestamp or datetime.now().strftime("%H:%M:%S")
        
        if msg_type == 'system':
            self.chat_display.insert(END, f"\n{text}\n", 'system')
        
        elif msg_type == 'error':
            self.chat_display.insert(END, f"\n⚠ {text}\n", 'error')
        
        elif msg_type == 'success':
            self.chat_display.insert(END, f"\n✓ {text}\n", 'success')
        
        elif msg_type == 'file':
            self.chat_display.insert(END, f"\n{text}\n", 'other')
        
        else:
            # Regular chat message
            prefix = "You" if is_own else sender
            tag = 'own' if is_own else 'other'
            
            self.chat_display.insert(END, f"\n[{ts}] ", 'timestamp')
            self.chat_display.insert(END, f"{prefix}: ", 'username')
            self.chat_display.insert(END, f"{text}\n", tag)
            
            # Save to history
            self._safe_call_async(self.message_manager.add(
                text=text, sender=sender, msg_type=msg_type,
                timestamp=datetime.now(), is_own=is_own, file_info=file_info
            ))
        
        self.chat_display.config(state=DISABLED)
        self.chat_display.see(END)
    
    def _display_message(self, msg: dict):
        """Display a loaded history message"""
        text = msg.get('text', msg.get('raw', ''))
        sender = msg.get('sender', 'system')
        msg_type = msg.get('type', 'text')
        ts = msg.get('timestamp', '')[:19].replace('T', ' ')[11:] if 'T' in msg.get('timestamp', '') else ''
        is_own = msg.get('is_own', False)
        
        self._add_message(text, sender=sender, msg_type=msg_type, 
                         timestamp=ts, is_own=is_own)
    
    def _set_connected(self, connected: bool, info: str = ""):
        """Update connection status UI"""
        self.connected = connected
        
        if connected:
            self.status_dot.config(fg=Config.SUCCESS_COLOR)
            self.status_label.config(text=info or "Connected")
            self.connect_btn.config(text="Disconnect", command=self._disconnect)
            self.message_entry.config(state='normal')
            self.send_btn.config(state='normal' if self.message_entry.get() else 'disabled')
            self.file_btn.config(state='normal')
        else:
            self.status_dot.config(fg=Config.ERROR_COLOR)
            self.status_label.config(text=info or "Disconnected")
            self.connect_btn.config(text="Connect", command=self._show_connect_dialog)
            self.message_entry.config(state='disabled' if not self.server_host else 'normal')
            self.send_btn.config(state='disabled')
            self.file_btn.config(state='disabled')
    
    def _set_status(self, text: str, color: str):
        """Update status bar"""
        self.status_label.config(text=text, fg=color)
    
    # ========================================================================
    # DIALOGS
    # ========================================================================
    
    def _show_connect_dialog(self):
        """Show connection dialog"""
        dialog = Tk()
        dialog.title("Connect to Server")
        dialog.geometry("320x200")
        dialog.configure(bg=Config.CHAT_BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center on parent
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 320) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")
        
        def on_connect():
            host = host_entry.get().strip() or "127.0.0.1"
            try:
                port = int(port_entry.get().strip() or "8888")
            except ValueError:
                messagebox.showerror("Error", "Invalid port", parent=dialog)
                return
            
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Enter your name", parent=dialog)
                return
            
            # Save settings
            self.server_host = host
            self.server_port = port
            self.username = name
            self._save_settings()
            
            dialog.destroy()
            
            if self.connected:
                self._safe_call_async(self.network.disconnect())
            
            self._safe_call_async(self._connect_async(host, port))
        
        # Fields
        Frame(dialog, bg=Config.CHAT_BG).pack(pady=10)
        
        Label(dialog, text="Server Host:", bg=Config.CHAT_BG, 
              fg=Config.CHAT_FG, font=Config.FONT_SMALL).pack()
        host_entry = Entry(dialog, width=30, font=Config.FONT_MAIN)
        host_entry.insert(0, self.server_host or "127.0.0.1")
        host_entry.pack(pady=2)
        
        Label(dialog, text="Port:", bg=Config.CHAT_BG, 
              fg=Config.CHAT_FG, font=Config.FONT_SMALL).pack()
        port_entry = Entry(dialog, width=30, font=Config.FONT_MAIN)
        port_entry.insert(0, str(self.server_port or "8888"))
        port_entry.pack(pady=2)
        
        Label(dialog, text="Your Name:", bg=Config.CHAT_BG, 
              fg=Config.CHAT_FG, font=Config.FONT_SMALL).pack()
        name_entry = Entry(dialog, width=30, font=Config.FONT_MAIN)
        name_entry.insert(0, self.username)
        name_entry.pack(pady=2)
        name_entry.focus_set()
        name_entry.bind('<Return>', lambda e: on_connect())
        
        # Buttons
        btn_frame = Frame(dialog, bg=Config.CHAT_BG)
        btn_frame.pack(pady=15)
        
        Button(btn_frame, text="Cancel", command=dialog.destroy,
               bg=Config.OTHER_MSG_BG, fg=Config.CHAT_FG, relief='flat',
               cursor='hand2', padx=20).pack(side='left', padx=5)
        
        Button(btn_frame, text="Connect", command=on_connect,
               bg=Config.ACCENT_COLOR, fg='white', relief='flat',
               cursor='hand2', padx=20).pack(side='left', padx=5)
        
        dialog.mainloop()
    
    def _show_settings(self):
        """Show settings dialog"""
        dialog = Tk()
        dialog.title("Settings")
        dialog.geometry("300x180")
        dialog.configure(bg=Config.CHAT_BG)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Current settings
        Label(dialog, text="Current Settings", bg=Config.CHAT_BG, 
              fg=Config.ACCENT_COLOR, font=Config.FONT_BOLD).pack(pady=10)
        
        settings = [
            f"Host: {self.server_host or 'Not set'}",
            f"Port: {self.server_port or 'Not set'}",
            f"Name: {self.username or 'Not set'}",
        ]
        for s in settings:
            Label(dialog, text=s, bg=Config.CHAT_BG, 
                  fg=Config.CHAT_FG, font=Config.FONT_SMALL).pack()
        
        # Buttons
        btn_frame = Frame(dialog, bg=Config.CHAT_BG)
        btn_frame.pack(pady=15)
        
        Button(btn_frame, text="Change", command=lambda: [dialog.destroy(), self._show_connect_dialog()],
               bg=Config.ACCENT_COLOR, fg='white', relief='flat', cursor='hand2', padx=15).pack(side='left', padx=5)
        
        Button(btn_frame, text="Close", command=dialog.destroy,
               bg=Config.OTHER_MSG_BG, fg=Config.CHAT_FG, relief='flat', cursor='hand2', padx=15).pack(side='left', padx=5)
        
        dialog.mainloop()
    
    def _disconnect(self):
        """Disconnect from server"""
        if self.network and self.connected:
            self._safe_call_async(self.network.disconnect())
    
    # ========================================================================
    # PERSISTENCE
    # ========================================================================
    
    def _load_settings(self):
        """Load saved settings"""
        try:
            if os.path.exists(Config.AUTH_FILE):
                with open(Config.AUTH_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.server_host = settings.get('host')
                    self.server_port = settings.get('port')
                    self.username = settings.get('username')
        except Exception as e:
            logger.error(f"Load settings error: {e}")
    
    def _save_settings(self):
        """Save settings"""
        try:
            settings = {
                'host': self.server_host,
                'port': self.server_port,
                'username': self.username
            }
            with open(Config.AUTH_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            logger.error(f"Save settings error: {e}")
    
    def _on_close(self):
        """Handle window close"""
        if self.connected and self.network:
            self._safe_call_async(self.network.disconnect())
        
        if not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        self.root.destroy()
    
    def run(self):
        """Start the application"""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()


# ============================================================================
# ENTRY POINT
# ============================================================================
def main():
    """Application entry point"""
    logger.info("O.L.E.G. Messenger GUI Client starting...")
    
    # Create TkinterDnD root
    root = TkinterDnD.Tk()
    
    # Create and run app
    app = ChatApp(root)
    app.run()
    
    logger.info("Client shutdown complete")


if __name__ == "__main__":
    main()