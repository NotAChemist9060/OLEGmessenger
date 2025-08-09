import asyncio
import os
import ctypes

no_escape=ctypes.windll.kernel32.GetConsoleWindow()

if no_escape:
    
    hmenu = ctypes.windll.user32.GetSystemMenu(no_escape, False)
    
    if hmenu:
        
        ctypes.windll.user32.EnableMenuItem(hmenu, 0xF060, 1|2)

# Устанавливаем заголовок консоли
ctypes.windll.kernel32.SetConsoleTitleW("O.L.E.G. messanger - You")
os.system('cls||clear')
print(' #####   #       #####   #####\n',
       '#   #   #       #       #    \n',
       '#   #   #       ####    #  ##\n',
       '#   #   #       #       #   #\n',
       '#####   #####   #####   #####\n')
print('=====The Client side=====')

async def receive_messages(reader):
    while True:
        try:
            data = await reader.read(1048576)
            if not data:
                print("\nConnection closed by server")
                break
            
            message = data.decode('utf-8')
            print(f"\n{message}", end='')
            print("> ", end='', flush=True)
            
        except (ConnectionResetError, asyncio.CancelledError):
            print("\nConnection reset by server")
            break
        except Exception as e:
            print(f"\nError while receiving message: {e}")
            break

async def send_messages(writer):
    try:
        while True:
            message = await asyncio.get_event_loop().run_in_executor(None, input, "> ")
            
            if message.lower() == ';exit':
                break
                
            writer.write(message.encode('utf-8'))
            await writer.drain()
            
    except Exception as e:
        print(f"Error occured while sending message: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    ip = input("Enter the IP address: ")
    port = int(input("Enter the port: "))
    name = input("Enter your name: ")
    
    try:
        while True:
            try:
                reader, writer = await asyncio.open_connection(ip, port)
                break
            except:
                pass
        writer.write(name.encode('utf-8'))
        await writer.drain()
        
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
        print("Goodbye")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye")

