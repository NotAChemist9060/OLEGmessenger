import asyncio
import os
import sys
import shutil
import json

'''no_escape=ctypes.windll.kernel32.GetConsoleWindow()

if no_escape:
    hmenu = ctypes.windll.user32.GetSystemMenu(no_escape, False)
    if hmenu:
        ctypes.windll.user32.EnableMenuItem(hmenu, 0xF060, 1|2)'''

# Устанавливаем заголовок консоли
if sys.platform == "win32":
    import ctypes
    ctypes.windll.kernel32.SetConsoleTitleW("O.L.E.G. messanger - You")
os.system("cls" if sys.platform == "win32" else "clear")

# Store the banner as a constant
BANNER ='''#####   #       #####   #####
#   #   #       #       #    
#   #   #       ####    #  ##
#   #   #       #       #   #
#####   #####   #####   #####'''

# ANSI escape sequences for cursor control
CURSOR_UP = '\033[F'
CURSOR_HIDE = '\033[?25l'
CURSOR_SHOW = '\033[?25h'
CLEAR_LINE = '\033[2K'
CLEAR_SCREEN = '\033[2J'
CURSOR_HOME = '\033[H'

# Store messages
text_to_write = []
input_buffer = ""  # Store current input

def get_terminal_size():
    """Get terminal dimensions"""
    return shutil.get_terminal_size((80, 24))

def clear_cmd():
    """Refresh the display without flashing"""
    # Hide cursor during update
    sys.stdout.write(CURSOR_HIDE)
    sys.stdout.flush()
    
    # Move cursor to top
    sys.stdout.write(CURSOR_HOME)
    
    # Clear from cursor to end of screen
    sys.stdout.write('\033[J')
    
    # Print banner
    print(BANNER)
    print('=====The Client side=====')
    
    # Print all messages
    for line in text_to_write[-get_terminal_size().lines + 6:]:  # Show only recent messages
        print(line)
    
    # Print input prompt with current buffer
    print(f"> {input_buffer}", end='', flush=True)
    
    # Show cursor again
    sys.stdout.write(CURSOR_SHOW)
    sys.stdout.flush()

def update_display(new_message=None):
    """Update display with new message without full clear"""
    global text_to_write
    
    if new_message:
        text_to_write.append(new_message)
    
    clear_cmd()

async def receive_messages(reader):
    global input_buffer, text_to_write
    
    while True:
        try:
            data = await reader.read(1048576)
            if not data:
                print("\nConnection closed by server")
                break

            message = data.decode('utf-8')
            
            # Save current input buffer
            current_input = input_buffer
            
            # Update display with new message
            update_display(message)
            
            # Restore input buffer
            input_buffer = current_input

        except (ConnectionResetError, asyncio.CancelledError):
            print("\nConnection reset by server")
            break
        except Exception as e:
            print(f"\nError while receiving message: {e}")
            break

async def send_messages(writer):
    global input_buffer, text_to_write
    
    try:
        while True:
            # Get character by character input (for better control)
            # But for simplicity, we'll still use input() here
            # If you want non-blocking character input, we'd need a more complex solution
            
            # Clear line and show prompt with current buffer
            sys.stdout.write(f"\r{CLEAR_LINE}> {input_buffer}")
            sys.stdout.flush()
            
            # Get input (this will block)
            message = await asyncio.get_event_loop().run_in_executor(None, input, "")
            
            if message != "":
                text_to_write.append("> " + message)
                
            if message.lower() == ';exit':
                break

            writer.write(message.encode('utf-8'))
            await writer.drain()
            
            # Clear input buffer
            input_buffer = ""
            
            # Refresh display
            clear_cmd()

    except Exception as e:
        print(f"Error occurred while sending message: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    global input_buffer
    
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

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye")