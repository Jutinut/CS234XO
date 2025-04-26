import os
import sys
import socket
import json
import base64

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
ENCODE_FORMAT = 'utf-8'

HOST = 'localhost'
PORT = 8080

def payloadByte(sender, receiver, functionName, data = None):
    payload_string = getPayload(sender, receiver, functionName, data)
    return bytes(payload_string, ENCODE_FORMAT)

def byteToJson(data_bytes):
    data = data_bytes.decode(ENCODE_FORMAT)
    data_json = json.loads(data)
    return data_json

def getPayload(sender, receiver, functionName, data = None):
    payload = {
        'sender': sender,
        'receiver': receiver,
        'type': functionName,
        'data': data
    }
    payload_string = json.dumps(payload)
    return payload_string

def getChoice(information, messageInput, limitChoice):
    choice = 0
    while choice <= 0 or choice > limitChoice:
        print(information)
        choice = str(input(messageInput))
        try:
            choice = int(choice)
            return choice
        except Exception as e:
            print(f"Unexpected {e=}, {type(e)=}")
            choice = 0
        print()
    return choice

def print_board(board):
    for row in board:
        print(" | ".join(row))
        print("-" * 9)

def testConnectToServer(client_tcp, SENDER_NAME):
    client_tcp.send(payloadByte(SENDER_NAME, 'receiver_test', 'test_server', {'example': 'string example data json'}))
    data_bytes = client_tcp.recv(1024)

def startPlaying(client_tcp, SENDER_NAME):
    # ขอเริ่มเกม
    client_tcp.send(payloadByte(SENDER_NAME, 'server', 'play'))

    while True:
        data_bytes = client_tcp.recv(4096)
        data_json = byteToJson(data_bytes)

        if data_json["msg"] == "DONE_PLAY":
            if 'board' in data_json:
            # ถ้า server บอกว่าจบเกมแล้ว
                print("=" * 33) # เพิ่มขีดเองงงงง
                print_board(data_json.get('board', [[' ']*3]*3))
            print(data_json["message"])
            break

        elif data_json["msg"] == "PLAY":
            if data_json.get("task") == "selectplace":
                # ถึงตาเราเล่น
                print_board(data_json['board'])
                print("\nYour turn (" + data_json["mark"] + ")")
                print(data_json["message"])

                # รับตำแหน่ง
                while True:
                    try:
                        move = input("Enter row and column (0-2) separated by space: ").split()
                        if len(move) != 2:
                            raise ValueError
                        x, y = int(move[0]), int(move[1])
                        if 0 <= x <= 2 and 0 <= y <= 2 and data_json['board'][x][y] == ' ':
                            break
                        else:
                            print("Invalid position or already taken. Try again.")
                    except:
                        print("Please enter two numbers between 0-2.")

                # วางตัวลงกระดาน
                data_json['board'][x][y] = data_json['mark']
                print_board(data_json['board'])     # <<< ✅ เพิ่มตรงนี้

                # ส่งข้อมูลกลับไป server
                client_tcp.send(payloadByte(
                    SENDER_NAME,
                    'server',
                    'take_turn',
                    {
                        'board': data_json['board'],
                        'mark': data_json['mark']
                    }
                ))

            else:
                # ยังไม่ถึงตาเรา รอข้อมูลใหม่
                
                print(data_json["message"])
                # รอข้อมูลรอบใหม่
                continue



def seeTheScore(client_tcp, SENDER_NAME):
    # ขอข้อมูลคะแนนจาก server
    client_tcp.send(payloadByte(SENDER_NAME, 'server', 'check_score'))

    # รับข้อมูลจาก server
    data_bytes = client_tcp.recv(2048)
    data_json = byteToJson(data_bytes)

    print("\n Score Board")
    print("-" * 33)
    print(f"| {'Name':<12} | {'Win':^3} | {'Lose':^4} | {'Tie':^3} |")
    print("-" * 33)

    for line in data_json['score']:
        parts = line.split()
        if len(parts) == 4:
            name, win, lose, tie = parts
            print(f"| {name:<12} | {win:^3} | {lose:^4} | {tie:^3} |")

    print("-" * 33)
    print()

def main():
    client_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_tcp.connect((HOST, PORT))
    
    SENDER_NAME = str(input("Enter your name: "))
    testConnectToServer(client_tcp, SENDER_NAME)
    isRun = True
    while isRun:
        choice = getChoice(
            '_____ Welcome to XO game _____\n1. Play \n2. See the score\n3. Exit\n_____________________________________', 
            'Enter your choice (1 or 2 or 3): ', 
            3
        )
        if choice == 1:
            startPlaying(client_tcp, SENDER_NAME)
        elif choice == 2:
            seeTheScore(client_tcp, SENDER_NAME)
        elif choice == 3:
            print("Good bye")
            isRun = False
            break

if __name__ == "__main__":
    main()
