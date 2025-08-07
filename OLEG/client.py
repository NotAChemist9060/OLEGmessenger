import asyncio
import os
import ctypes

# Устанавливаем заголовок консоли
ctypes.windll.kernel32.SetConsoleTitleW("O.L.E.G. messanger - Вы")
os.system('cls||clear')
print(' #####   #       #####   #####\n',
       '#   #   #       #       #    \n',
       '#   #   #       ####    #  ##\n',
       '#   #   #       #       #   #\n',
       '#####   #####   #####   #####\n')
print('=====The Client side=====')

async def receive_messages(reader):
    """
    Асинхронная задача для получения сообщений от сервера
    """
    while True:
        try:
            data = await reader.read(1024)  # Читаем данные
            if not data:  # Если соединение закрыто
                print("\nСоединение с сервером разорвано")
                break
            
            message = data.decode('utf-8')
            # Выводим сообщение с новой строки, но без лишних переносов
            print(f"\n{message}", end='')
            # Выводим приглашение для ввода с новой строки
            print("> ", end='', flush=True)
            
        except (ConnectionResetError, asyncio.CancelledError):
            print("\nСоединение прервано")
            break
        except Exception as e:
            print(f"\nОшибка при получении сообщения: {e}")
            break

async def send_messages(writer):
    """
    Асинхронная задача для отправки сообщений
    """
    try:
        while True:
            # Используем run_in_executor, так как input() блокирующий
            message = await asyncio.get_event_loop().run_in_executor(None, input, "> ")
            
            if message.lower() == ':exit:':
                break
                
            writer.write(message.encode('utf-8'))
            await writer.drain()  # Обеспечиваем отправку
            
    except Exception as e:
        print(f"Ошибка при отправке: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    
    # Подключение к серверу
    ip = input("Введите IP сервера: ")
    port = int(input("Введите порт сервера: "))
    name = input("Введите ваше имя: ")
    
    try:
        while True:
            try:
                reader, writer = await asyncio.open_connection(ip, port)
                break
            except:
                pass
        # Отправляем серверу свое имя
        writer.write(name.encode('utf-8'))
        await writer.drain()
        
        # Запускаем задачу для получения сообщений
        receive_task = asyncio.create_task(receive_messages(reader))
        
        # Основной цикл отправки сообщений
        await send_messages(writer)
        
        # Отменяем задачу получения при выходе
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
            
    except ConnectionRefusedError:
        print("Не удалось подключиться к серверу")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    finally:
        print("Выход из мессенджера")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПриложение завершено")
