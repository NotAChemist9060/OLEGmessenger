import socket
import ctypes; ctypes.windll.kernel32.SetConsoleTitleW("O.L.E.G. messanger, " + "You")


ip = str(input('Ip: '))
port = int(input('Port: '))
name = str(input('Name: '))
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def connect(ip, port, name):
    try:
        client_socket.connect((ip, port))
        client_socket.send(name.encode('utf-8'))
    except ConnectionRefusedError:
        print("Connection refused. Server may be down.")
        exit()

def main():
    while True:
        try:
            message = input()
            if message == '':
                message = 'пустое сообщение отправитель долбаеб'
            elif message == ':exit:':
                client_socket.close()
                break
            client_socket.send(message.encode('utf-8'))
            response = client_socket.recv(1024)
            print("Server response:", response.decode('utf-8'))
        except ConnectionResetError:
            print("Server disconnected.")
            break
        except Exception as e:
            print("Error occurred:", e)
            break

connect(ip, port, name)
main()