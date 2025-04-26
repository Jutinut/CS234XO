import select
import socket
import sys
import queue
import os
import json
import base64

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

SERVER_FOLDER = 'Server'
FILE_MEMBER = 'member.txt'
FILE_MEMBER_WITH_SCORE = 'member_score.txt'

HOST = 'localhost'
PORT = 8080

server_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # prevents "already in use" errors
server_tcp.setblocking(0)
server_tcp.bind((HOST, PORT))
server_tcp.listen(5)

server_udp = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
server_udp.bind((HOST,PORT))

inputs = [server_udp,server_tcp]
outputs = []
message_queues = {}
online_client_connection = {}
online_client_name = {} 
board = [[' ' for _ in range(3)] for _ in range(3)]
player_mark = {'X':'','O':''}
isPlay = False

def append_name_to_file(name):
    try:
        directory = os.path.join(CURRENT_PATH, SERVER_FOLDER)
        if not os.path.exists(directory):
            os.makedirs(directory)
    except Exception as e:
        print(f"Unexpected {e=}, {type(e)=}")

    try:
        with open(f'{SERVER_FOLDER}/{FILE_MEMBER}', 'r') as f:
            existing_names = {line.strip() for line in f}
        if name not in existing_names:
            with open(f'{SERVER_FOLDER}/{FILE_MEMBER}', 'a') as f:
                f.write(name + '\n')
    except FileNotFoundError:
        with open(f'{SERVER_FOLDER}/{FILE_MEMBER}', 'w') as f: 
            f.write(name + '\n')
    except Exception as e:
        print(f"Unexpected {e=}, {type(e)=}")

def append_name_and_score_to_file(name,win,lose,tie):
    try:
        directory = os.path.join(CURRENT_PATH, SERVER_FOLDER)
        if not os.path.exists(directory):
            os.makedirs(directory)
    except Exception as e:
        print(f"Unexpected {e=}, {type(e)=}")
    existing_names = []
    try:
        with open(f'{SERVER_FOLDER}/{FILE_MEMBER_WITH_SCORE}', 'r') as f:
            for line in f:
                line_split = line.split()
                existing_names.append(line_split[0])
        if name not in existing_names:
            with open(f'{SERVER_FOLDER}/{FILE_MEMBER_WITH_SCORE}', 'a') as f:
                f.write(name + "\t" + str(win) + "\t" + str(lose) + "\t" + str(tie) + '\n')
        else:
            newline=[]
            with open(f'{SERVER_FOLDER}/{FILE_MEMBER_WITH_SCORE}',"r") as f:
                for line in f:     
                    line_split = line.split()
                    if line_split[0] != name:
                        newline.append(line)
                    else:
                        newline.append(name + "\t" + str(win) + "\t" + str(lose) + "\t" + str(tie) + '\n')
            with open(f'{SERVER_FOLDER}/{FILE_MEMBER_WITH_SCORE}',"w") as f:
                for line in newline:
                    f.writelines(line)
    except FileNotFoundError:
        with open(f'{SERVER_FOLDER}/{FILE_MEMBER_WITH_SCORE}', 'w') as f: 
            f.write(name + "\t0\t0\t0\n") #แก้ให้เริ่มต้น Score เป็น 0 0 0
    except Exception as e:
        print(f"Unexpected {e=}, {type(e)=}")
        
def get_list_member():
    names = []
    with open(f'{SERVER_FOLDER}/{FILE_MEMBER}', 'r') as f:
        for line in f:
            names.append(line.strip())
    return names

def get_list_member_with_score():
    score = []
    with open(f'{SERVER_FOLDER}/{FILE_MEMBER_WITH_SCORE}', 'r') as f:
        for line in f:
            score.append(line.strip())
    return score

def get_score(name):
    win = 0
    lose = 0
    tie = 0
    try:
        with open(f'{SERVER_FOLDER}/{FILE_MEMBER_WITH_SCORE}', 'r') as f:
            for line in f:
                line_split = line.split()
                if name == line_split[0]:
                    win = int(line_split[1])
                    lose = int(line_split[2])
                    tie = int(line_split[3])
    except FileNotFoundError:
        pass 
    return win, lose, tie


def get_board():
    return board

def reset_mark():
    player_mark.clear()
    player_mark.update({'X': '', 'O': ''}) 

def reset_queue():
    message_queues.clear() 

def check_winner(board, mark):
    # Check rows and columns
    for i in range(3):
        if all(board[i][j] == mark for j in range(3)) or all(board[j][i] == mark for j in range(3)):
            return True
    # Check diagonals
    if all(board[i][i] == mark for i in range(3)) or all(board[i][2 - i] == mark for i in range(3)):
        return True
    return False

def is_full(board):
    return all(cell in ('X', 'O') for row in board for cell in row)

def find_key(player_mark, name):
    for key, val in player_mark.items():
        if val == name: return key
    return "None"

def main():
    print(f'Running Server Host:{HOST}, Port:{PORT}')
    while inputs:
        try:
            readable, writable, exceptional = select.select(inputs, outputs, inputs)
            for s in readable:
                if s is server_tcp:
                    connection, client_address = s.accept()
                    connection.setblocking(0)
                    inputs.append(connection)
                    print("Received connection request from: ", client_address)
                    message_queues[connection] = queue.Queue()

                elif s is server_udp:
                    data, addr = s.recvfrom(1024)
                    if data:
                        print("data received over UDP: ", data)
                        data = ("ACK - data received: "+str(data)).encode()
                        s.sendto(data,addr)

                else:
                    data_bytes = s.recv(1024)
                    print("data bytes received over TCP: ",data_bytes, type(data_bytes), len(data_bytes))

                    if(len(data_bytes) == 0):
                        try:
                            inputs.remove(s)
                            if s in outputs:
                                outputs.remove(s)
                            s.close()
                            del message_queues[s]
                            name = online_client_name[s]
                            del online_client_connection[name]
                        except Exception as e:
                            print(f"Unexpected {e=}, {type(e)=}")
                        
                    if data_bytes:
                        global isPlay
                        data = data_bytes.decode('utf-8')
                        payload = json.loads(data)
                        if('sender' in payload and 'receiver' in payload and 'type' in payload and 'data' in payload):
                            payloadType = payload['type']
                            if(payloadType == 'check_score'):
                                senderName = payload['sender']
                                receiverConnection = online_client_connection[senderName]
                                score = get_list_member_with_score()
                                payload = {
                                    'status': 200,
                                    'msg': 'OK',
                                    'score': score
                                }
                                payload_string = json.dumps(payload)
                                receiverConnection.send(bytes(payload_string, 'utf-8'))
                            elif(payloadType == 'play'):
                                senderName = payload['sender']
                                if not isPlay:
                                    if player_mark['X'] == '':
                                        player_mark['X'] = senderName
                                    if player_mark['X'] == '':
                                        player_mark['X'] = senderName

                                        # <<< เพิ่มส่ง "Waiting for another player"
                                        receiverConnection = online_client_connection[senderName]
                                        payload = {
                                            'status': 200,
                                            'msg': 'PLAY',
                                            'sender': senderName,
                                            'message': "Waiting for another player to join..."
                                        }
                                        payload_string = json.dumps(payload)
                                        receiverConnection.send(bytes(payload_string, 'utf-8'))

                                        
                                    elif player_mark['O'] == '':
                                        player_mark['O'] = senderName
                                        isPlay = True
                                else:
                                    receiverConnection = online_client_connection[senderName]
                                    payload = {
                                        'status': 200,
                                        'msg': 'DONE_PLAY',
                                        'sender': senderName,
                                        'message': "Waiting for next round"
                                    }
                                    payload_string = json.dumps(payload)
                                    receiverConnection.send(bytes(payload_string, 'utf-8'))
                                if (senderName == player_mark['O'] or senderName == player_mark['X']):
                                    if player_mark['O'] == '':
                                        receiverConnection = online_client_connection[senderName]
                                        payload = {
                                            'status': 200,
                                            'msg': 'OK',
                                            'sender': senderName,
                                            'message': "Waiting for another player"
                                        }
                                        payload_string = json.dumps(payload)
                                        message_queues[s].put(bytes(payload_string, 'utf-8'))

                                        if s not in outputs:
                                            outputs.append(s)
                                    else:
                                        # Player one get to play first
                                        receiverConnection = online_client_connection[player_mark['X']]
                                        board_info = get_board()
                                        payload = {
                                            'status': 200,
                                            'msg': 'PLAY',
                                            'sender': player_mark['X'],
                                            'mark': 'X',
                                            'board': board_info,
                                            'task': "selectplace",
                                            'message': "Select where to place "
                                        }
                                        payload_string = json.dumps(payload)
                                        receiverConnection.send(bytes(payload_string, 'utf-8'))

                                        # Player two wait to play
                                        receiverConnection = online_client_connection[player_mark['O']]
                                        payload = {
                                            'status': 200,
                                            'msg': 'PLAY',
                                            'sender': player_mark['O'],
                                            'message': "Starting now! Waiting for another player"
                                        }
                                        payload_string = json.dumps(payload)
                                        receiverConnection.send(bytes(payload_string, 'utf-8'))
                            elif(payloadType == 'take_turn'):
                                senderName = payload['sender']
                                board = payload['data']['board']
                                mark = payload['data']['mark']
                                if check_winner(board, mark) == True:
                                    if mark == 'X':
                                        receiver = player_mark['O']
                                    else:
                                        receiver = player_mark['X']
                                    receiverConnection = online_client_connection[receiver]
                                    payload = {
                                        'status': 200,
                                        'msg': 'DONE_PLAY',
                                        'receiver': receiver,
                                        'board': board,
                                        'message': "You lose!!"
                                    }
                                    win, lose, tie = get_score(receiver)
                                    append_name_and_score_to_file(receiver,win,lose+1,tie)
                                    payload_string = json.dumps(payload)
                                    receiverConnection.send(bytes(payload_string, 'utf-8'))
                                    receiverConnection = online_client_connection[senderName]
                                    payload = {
                                        'status': 200,
                                        'msg': 'DONE_PLAY',
                                        'board': board,
                                        'receiver': senderName,
                                        'message': "You win!!"
                                    }
                                    win, lose, tie = get_score(senderName)
                                    append_name_and_score_to_file(senderName,win+1,lose,tie)
                                    payload_string = json.dumps(payload)
                                    receiverConnection.send(bytes(payload_string, 'utf-8'))
                                    reset_mark()
                                    print(player_mark)
                                    isPlay = False
                                elif is_full(board):
                                    if mark == 'X':
                                        receiver = player_mark['O']
                                    else:
                                        receiver = player_mark['X']
                                    receiverConnection = online_client_connection[receiver]
                                    payload = {
                                        'status': 200,
                                        'msg': 'DONE_PLAY',
                                        'receiver': receiver,
                                        'message': "TIE!!"
                                    }
                                    win, lose, tie = get_score(receiver)
                                    append_name_and_score_to_file(receiver,win,lose,tie+1)
                                    payload_string = json.dumps(payload)
                                    receiverConnection.send(bytes(payload_string, 'utf-8'))
                                    receiverConnection = online_client_connection[senderName]
                                    payload = {
                                        'status': 200,
                                        'msg': 'DONE_PLAY',
                                        'receiver': senderName,
                                        'message': "TIE!!"
                                    }
                                    win, lose, tie = get_score(senderName)
                                    append_name_and_score_to_file(senderName,win,lose,tie+1)
                                    payload_string = json.dumps(payload)
                                    receiverConnection.send(bytes(payload_string, 'utf-8'))
                                    reset_mark()
                                    print(player_mark)
                                    isPlay = False
                                else:
                                    if mark == 'X':
                                        receiverConnection = online_client_connection[player_mark['O']]
                                        payload = {
                                            'status': 200,
                                            'msg': 'PLAY',
                                            'sender': player_mark['O'],
                                            'mark': 'O',
                                            'board': board,
                                            'task': "selectplace",
                                            'message': "Select where to place "
                                        }
                                        payload_string = json.dumps(payload)
                                        receiverConnection.send(bytes(payload_string, 'utf-8'))

                                        # Player two wait to play
                                        receiverConnection = online_client_connection[player_mark['X']]
                                        payload = {
                                            'status': 200,
                                            'msg': 'PLAY',
                                            'sender': senderName,
                                            'message': "Waiting for another player"
                                        }
                                        payload_string = json.dumps(payload)
                                        receiverConnection.send(bytes(payload_string, 'utf-8'))
                                    else:
                                        receiverConnection = online_client_connection[player_mark['X']]
                                        payload = {
                                            'status': 200,
                                            'msg': 'PLAY',
                                            'sender': player_mark['X'],
                                            'mark': 'X',
                                            'board': board,
                                            'task': "selectplace",
                                            'message': "Select where to place "
                                        }
                                        payload_string = json.dumps(payload)
                                        receiverConnection.send(bytes(payload_string, 'utf-8'))

                                        # Player two wait to play
                                        receiverConnection = online_client_connection[player_mark['O']]
                                        payload = {
                                            'status': 200,
                                            'msg': 'PLAY',
                                            'sender': senderName,
                                            'message': "Waiting for another player"
                                        }
                                        payload_string = json.dumps(payload)
                                        receiverConnection.send(bytes(payload_string, 'utf-8'))
                            
                            elif(payloadType == 'test_server'):
                                sender = payload['sender']
                                senderName = payload['sender']
                                online_client_connection[senderName] = s
                                online_client_name[s] = senderName
                                append_name_to_file(sender)
                                win, lose, tie = get_score(senderName)
                                append_name_and_score_to_file(senderName,win,lose,tie)
                                receiver = payload['receiver']
                                data = payload['data']
                                payload = {
                                    'status': 200,
                                    'msg': 'This is test message from server.',
                                    'sender': sender,
                                    'receiver': receiver,
                                    'data': data
                                }
                                payload_string = json.dumps(payload)
                                message_queues[s].put(bytes(payload_string, 'utf-8'))

                                if s not in outputs:
                                    outputs.append(s)

                        else:
                            ack_msg = "Incorrect Payload!"
                            message_queues[s].put(bytes(ack_msg, 'utf-8'))
                            if s not in outputs:
                                outputs.append(s)

                    else:
                        print("No data")

            for s in writable:
                if not message_queues[s].empty():
                    next_msg = message_queues[s].get()
                    s.send(next_msg)       
                else:
                    outputs.remove(s)

            for s in exceptional:
                inputs.remove(s)
                if s in outputs:
                    outputs.remove(s)
                s.close()
                del message_queues[s]

        except Exception as e:
            print(f"Unexpected {e=}, {type(e)=}")

if __name__ == "__main__":
    main()
