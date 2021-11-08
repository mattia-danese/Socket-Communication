from os import pardir, write
import socket
import sys
import signal #CTRL-C and CTRL-D Trap
import argparse
import select

# parser = argparse.ArgumentParser(description='Connect to or host an IM client.')
# parser.add_argument('--s', action="store_true")
# parser.add_argument('--c', action="store_true")
# parser.add_argument('hostname', action="store_true")

        # if socket is server, all client sockets must be closed first
        # if isServer:
            # for c in client_sockets:
            #     if c is not sys.stdin:
            #         c.close()
            # socket.close()

        # else:



def main(argv):
    def handler(signal, frame):
        sys.stdout.write("\nCLTR-C has been received. Socket disconnected.\n")
        socket.close()
        sys.exit()

    if len(argv) == 1:
        socket = server(argv)
        isServer = True
    elif len(argv) == 2:
        socket = client(argv)
        isServer = False
    else:
        print("Wrong input format!")
        return

    client_sockets = [socket]
    signal.signal(signal.SIGINT, handler)
    
    while True:
        read_list = [sys.stdin] + client_sockets
        (ready_read,_,_) = select.select(read_list, [], [])

        for sock in ready_read:
            if sock is sys.stdin:
                data = sys.stdin.readline()
                # 'socket' is client socket returned by both 'client' and 'server' functions
                socket.send(data.encode())
            else:
                data = sock.recv(1024).decode()
                if data != "":
                    sys.stdout.write(data)
                    sys.stdout.flush()
                else:
                    client_sockets.remove(sock)
                    sock.close()
    



def client(args):
    if args[0] != '--c':
        print("Wrong input format!")
        return

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((args[1], 9999)) #connect to host at port 9999
    print("Connected to server at {}:{}".format(args[1], 9999))

    return s


def server(args):
    if args[0] != '--s':
        print("Wrong input format!")
        return

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 9999)) #bound to port 9999
    s.listen(1) #'backlog' of socket
    print("Host is listening at 127.0.0.1:9999...")

    conn, addr = s.accept()
    print("{}:{} has connected...".format(addr[0], addr[1]))
    return conn

if __name__ == "__main__":
    main(sys.argv[1:])