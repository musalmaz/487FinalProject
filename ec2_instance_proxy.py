# import socket
# import json

# def decrypt_request(encrypted_request):
#     # Implement your decryption logic
#     decrypted_request = json.loads(encrypted_request)  # Example: Convert JSON string to request object
#     return decrypted_request

# def perform_website_search(website_url):
#     # Implement your logic to search for the website
#     # Return the encrypted response
#     pass

# def encrypt_response(response):
#     # Implement your encryption logic
#     encrypted_response = json.dumps(response)  # Example: Convert response to JSON string
#     return encrypted_response

# # Create a TCP listener on the proxy server
# proxy_address = ('', 8080)  # Replace with the desired address and port
# sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# sock.bind(proxy_address)
# sock.listen(1)

# while True:
#     # Accept incoming connections
#     client_socket, client_address = sock.accept()
    
#     # Receive the encrypted request from the local machine
#     encrypted_request = client_socket.recv(4096).decode()
    
#     # Decrypt the request
#     decrypted_request = decrypt_request(encrypted_request)
    
#     # Extract the website URL from the decrypted request
#     website_url = decrypted_request['website']
    
#     # Perform the website search or any other processing logic
#     search_result = perform_website_search(website_url)
    
#     # Encrypt the search result
#     encrypted_response = encrypt_response(search_result)
    
#     # Send the encrypted response back to the local machine
#     client_socket.send(encrypted_response.encode())
    
#     # Close the connection with the local machine
#     client_socket.close()

import socket
import threading
import sys
import subprocess
import time
import random
import json
from pyDes import triple_des, PAD_PKCS5
port = int(input("Port : "))
class EC2_Proxy():
    def __init__(self):
        self.PORT = port
        self.bit_length_key = 6
        self.B = 0
        self.key = ""
        self.local_ip = ""
        self.is_key_exchange_completed = False
        
    def listener(self): 
        while(True):
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client.bind(("", self.PORT))
            client.listen()
            s, address = client.accept()
            self.local_ip = address[0]
            print("ip: ", address[0])
            msg = s.recv(1024*1024)           
            print("msg as bytes: ", msg)
            # this if is for key exchange
            if not self.is_key_exchange_completed:
                coming_msg = msg.decode()
                msg_ = json.loads(coming_msg)
                if msg_['type'] == "key":  # connection is established,calculate B and send
                    p = msg_['p']
                    g = msg_['g']
                    A = msg_['A']
                    b = random.randint(100, 1000)  # change those values
                    # B = g^b mod(p)
                    g = int(g)
                    p = int(p)
                    A = int(A)
                    self.B = pow(g,b) % p
                    # key = A^b mod(p)
                    key = pow(A, b) % p
                    self.key = str(key)
                    print("key: ",self.key)
                    self.is_key_exchange_completed = True
            else:
                # Implement your decryption logic
                msg_padded = msg.ljust((len(msg)//8 + 1) * 8)
                recovered_msg = triple_des(self.key.ljust(24)).decrypt(msg, padmode=PAD_PKCS5)
                # since recovered msg is type bytes, turn it as json format
                recovered_msg = recovered_msg.decode()
                recovered_msg = json.loads(recovered_msg)

                # Extract the website URL from the decrypted request
                website_url = recovered_msg['website']
                # Perform the website search or any other processing logic
                search_result = self.perform_website_search(website_url)
                # Encrypt the search result
                search_result_encrypted = triple_des(self.key.ljust(24)).encrypt(search_result, padmode=PAD_PKCS5)
                # I am not sure this part will work
                # Send encrypted search result back to client
                s.sendall(search_result_encrypted)

                s.close()
    


    def perform_website_search(self,website_url):
        # Implement your logic to search for the website
        # Return the encrypted response
        pass

    def decrypt_request(encrypted_request):
        # Implement your decryption logic
        decrypted_request = json.loads(encrypted_request)  # Example: Convert JSON string to request object
        return decrypted_request

    def sender(self):
        while not self.is_key_exchange_completed:
            try:
                if self.B != 0:
                    key_msg = str({"type" : "key", "B" : f"{self.B}"}).replace("'", '"')
                    key_sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    key_sender.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 2)
                    key_sender.connect((self.local_ip,self.PORT))
                    key_sender.send(key_msg.encode())
                    self.B = 0
            except:
                pass
        print("key exchange completed")

if __name__ == "__main__":
    proxy = EC2_Proxy()
    ec2_listener = threading.Thread(target=proxy.listener)
    #ec2_sender = threading.Thread(target=proxy.sender)

    ec2_listener.start()
    proxy.sender()
    #ec2_sender.start()

    ec2_listener.join()
    #ec2_sender.join()