
# hw1p2.py

import argparse
import select
import socket
import sys
import signal
from Crypto import Random
from Crypto.Hash import SHA256, HMAC
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import struct



# define some globals
HOST = ''
PORT = 9999
SOCKET_LIST = []
K1 = ''
K2 = ''



def handler(signum,frame):
    """ handle a SIGINT (ctrl-C) keypress """
    for s in SOCKET_LIST:                 #close all sockets
        s.close()
    sys.exit(0)

    

def wait_for_incoming_connection():
    """
    create a server socket and wait for incoming connection

    returns the server socket
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)
    conn, addr = s.accept()
    SOCKET_LIST.append(s)
    SOCKET_LIST.append(conn)
    return conn


def connect_to_host( dst ):
    """ connects to the host 'dst' """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect( (dst,PORT) )
        SOCKET_LIST.append(s)
        return s
    except socket.error:
        print( "Could not connect to %s." % dst )
        sys.exit(0)
    


def parse_command_line():
    """ parse the command-line """
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--c", dest="dst", help="destination address")
    parser.add_argument("-s", "--s", dest="server", action="store_true",
                    default=False, help="start server mode")
    parser.add_argument("--confkey", dest="K1", required=True, help="confidentiality key used for encryption")
    parser.add_argument("--authkey", dest="K2", required=True, help="authenticity key for HMAC")

    options = parser.parse_args()
 
    if (not options.dst and not options.server) and (not options.K1 or not options.K2):
        parser.print_help()
        parser.error("must specify either server or client mode, the confidentiality key, and the authenticity key")

    return options

def encryptData(data):
    length = str(len(data)).encode()

    if len(data) > 15:
        curr_data = data[:15]
        more_data = data[15:]
    else:
        curr_data = data
        more_data = ""
  
    # initialization vector
    iv = Random.get_random_bytes(AES.block_size)

    # creating cipher object
    cipher = AES.new(K1, AES.MODE_CBC, iv)

    # encrypting using AES-256 in CBC mode
    encrypt_length = cipher.encrypt(pad(length, 16))
    encrypt_data = cipher.encrypt(pad(curr_data.encode(), 16))

    # generating HMACs using SHA256
    hmac_encrypt_length = HMAC.new(K2, digestmod=SHA256).update(iv + encrypt_length).digest()
    hmac_encrypt_data = HMAC.new(K2, digestmod=SHA256).update(encrypt_data).digest()


    # final message (what is being sent)
    return iv + encrypt_length + hmac_encrypt_length + encrypt_data + hmac_encrypt_data, more_data

def decryptData(data):
    # extracting parts from data
    iv = data[:AES.block_size]
    
    encrypt_length = data[AES.block_size:AES.block_size*2]
    hmac_encrypt_length = data[AES.block_size*2:AES.block_size*2 + 32] #256 bits = 32 bytes
    
    encrypt_data = data[AES.block_size*2 + 32:AES.block_size*3 + 32]
    hmac_encrypt_data = data[AES.block_size*3 + 32:]
    
    # verifying HMACs
    hmac_length = HMAC.new(K2, digestmod=SHA256).update(iv + encrypt_length)
    try:
        hmac_length.verify(hmac_encrypt_length)
    except ValueError:
        sys.stdout.write("ERROR: HMAC verification failed")
        handler(None, None)
   
    hmac_data = HMAC.new(K2, digestmod=SHA256).update(encrypt_data)
    try:
        hmac_data.verify(hmac_encrypt_data)
    except ValueError:
        sys.stdout.write("ERROR: HMAC verification failed")
        handler(None, None)

    # creating cipher
    cipher = AES.new(K1, AES.MODE_CBC, iv)

    decrypt_length = unpad(cipher.decrypt(encrypt_length), 16)
    decrypt_msg    = unpad(cipher.decrypt(encrypt_data), 16)

    return decrypt_msg.decode()


if __name__ == "__main__":

    options = parse_command_line()

    # hashes both keys to esnure they have length of 256 bits
    hasher = SHA256.new()
    
    hasher.update(options.K1.encode("utf8"))
    K1 = hasher.digest()

    hasher.update(options.K2.encode("utf8"))
    K2 = hasher.digest()


    # catch when the user presses CTRL-C
    signal.signal(signal.SIGINT,handler)

    if options.server:
        s = wait_for_incoming_connection()
    elif options.dst:
        s = connect_to_host(options.dst)
    else:
        assert(False)                         # this shouldn't happen

    rlist = [ s, sys.stdin ]
    wlist = []
    xlist = []

    while True:
        (r, w, x) = select.select(rlist,wlist,xlist)
        if s in r:                            # there is data to read from network
            data = s.recv(112)
            if data == b'':                    # other side ended connection
                break
            data = decryptData(data)
            sys.stdout.write(data)            # READING ENCRYPTED DATA (MUST DECRYPT)
            sys.stdout.flush()
            
        if sys.stdin in r:                    # there is data to read from stdin
            data = sys.stdin.readline()
            data, more_data = encryptData(data)          # SENDING ENCRYPTED DATA

            if data == "":                    # we closed STDIN
                break

            s.send(data)

            while more_data != "":
                # print("IN WHILE LOOP")
                data, more_data = encryptData(more_data)
                s.send(data)

    """
            If we get here, then we've got an EOF in either stdin or our network.
            In either case, we iterate through our open sockets and close them.
    """
    for sock in SOCKET_LIST:
        sock.close()

    sys.exit(0)                           # all's well that ends well!