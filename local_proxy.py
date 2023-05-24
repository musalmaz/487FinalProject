# import socket
# import json
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options

# def encrypt_request(request):
#     # Implement your encryption logic
#     encrypted_request = json.dumps(request)  # Example: Convert request to JSON string
#     return encrypted_request

# def decrypt_response(response):
#     # Implement your decryption logic
#     decrypted_response = json.loads(response)  # Example: Convert JSON string to response object
#     return decrypted_response

# def open_website_in_chrome(website_url):
#     options = Options()
#     # Add any necessary options for Chrome

#     driver = webdriver.Chrome(options=options)
#     driver.get(website_url)

# # Connect to the proxy server
# proxy_address = ('proxy-server-address', 8080)  # Replace with your actual proxy server address and port
# sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# sock.connect(proxy_address)

# # Initialize the WebDriver
# options = Options()
# # Add any necessary options for Chrome
# driver = webdriver.Chrome(options=options)

# # Start the main loop
# while True:
#     # Retrieve the website URL from the active Chrome browser
#     website_url = driver.current_url

#     # Create the request dictionary
#     request = {
#         "myIP": "...",
#         "website": website_url
#     }

#     # Encrypt the request
#     encrypted_request = encrypt_request(request)

#     # Send the encrypted request to the proxy server
#     sock.send(encrypted_request.encode())

#     # Receive the encrypted response from the proxy server
#     encrypted_response = sock.recv(4096).decode()

#     # Decrypt the response
#     decrypted_response = decrypt_response(encrypted_response)

#     # Process the decrypted response
#     # ...

#     # Open the website in Chrome browser on the local machine
#     open_website_in_chrome(decrypted_response['website'])

# # Close the TCP connection
# sock.close()

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import socket
import threading
import sys
import subprocess
import time
import random
import json
from sympy import isprime
import pyDes
port = int(input("port : "))
conn_ip = input("connection_ip : ")

class Local_Proxy():
    def __init__(self):
        self.PORT = port
        self.bit_length_key = 6
        self.conn_ip = conn_ip
        self.key = ""
        self.a  = random.randint(100, 1000)  # change those values
        self.g = self.generate_random_prime()
        self.p = self.generate_random_prime()
        self.is_key_exchange_completed = False

        # Initialize the WebDriver
        self.options = Options()
        # Add any necessary options for Chrome
        self.driver = webdriver.Chrome(options=self.options)
    # send messages to ec2
    # message should be string
    def proxy_sender(self, msg): 
        while True:
            try:                                  
                sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sender.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sender.connect((self.conn_ip,self.PORT))
                # Retrieve the website URL from the active Chrome browser
                website_url = self.driver.current_url
                # Create the request dictionary
                request = {
                    "myIP": "...",
                    "website": website_url
                }
                # convert request o string
                request_str = json.dumps(request)
                # Encrypt the request
                encoded_msg = pyDes.triple_des(self.key.ljust(24)).encrypt(request_str, padmode=2)
                print("encoded msg: ", request_str)
                sender.send(encoded_msg)
                sender.close()
            except:
                print("error !!!")
    # get the required key for encryption
    def keySender(self): 
        try:          
            # A = g^a mod(p)  a is random
            A = pow(self.g,self.a) % self.p
            msg = str({"type" : "key", "g" : f"{self.g}", "p" : f"{self.p}", "A" : f"{A}"}).replace("'", '"')
            key_sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            key_sender.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 2)
            print("ip: ", self.conn_ip)
            key_sender.connect((self.conn_ip,self.PORT))
            key_sender.send(msg.encode())
            key_sender.close()
        except socket.error as e:
            print(e)

    def open_website_in_chrome(self,website_url):
        options = Options()
        # Add any necessary options for Chrome
        driver = webdriver.Chrome(options=options)
        driver.get(website_url)

    def proxy_listener(self): 
        while(True):
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client.bind(("", self.PORT))
            client.listen()
            s, address = client.accept()
            msg = s.recv(1024*1024)           
            
            if not self.is_key_exchange_completed:
                coming_msg = msg.decode()
                msg_ = json.loads(coming_msg)
                if msg_['type'] == "key":  # connection is established,calculate B and send 
                    B = msg_['B']
                    B = int(B)
                    # key = B^a mod(p)
                    key = pow(B, self.a) % self.p
                    print("key int: ", key)
                    self.key = str(key)
                    self.is_key_exchange_completed = True
                print(coming_msg)
            else:
                # msg that comes from ec2
                msg_padded = msg.ljust((len(msg)//8 + 1) * 8)
                recovered_msg = pyDes.triple_des(self.key.ljust(24)).decrypt(msg, padmode=pyDes.PAD_PKCS5)
                print("recovered msg: ", recovered_msg)
                recovered_msg = recovered_msg.decode()
                recovered_msg = json.loads(recovered_msg)
                # Process the decrypted response
                # ...

                # Open the website in Chrome browser on the local machine
                self.open_website_in_chrome(recovered_msg['website'])


    def generate_random_prime(self):
        while True:
            num = random.getrandbits(self.bit_length_key)  # Generate a random number with the specified bit length
            if num % 2 == 0:  # Ensure the number is odd
                num += 1
            if isprime(num):  # Check if the number is prime
                return num
    
    def get_userIP(self): # get users's ip 
        command = "hostname -I"
        cmd = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        shell_return = cmd.stdout.read()
        sb_return = shell_return.decode()
        userIP = sb_return[0:-2]
        split = userIP.split(" ")
        userIP = split[0]
        print("host ip : ", userIP)
        return userIP
    
    
proxy = Local_Proxy()
# def menu():
#     print("s to send, w to wait, e to exit")
#     option = input()
#     if option == "s":
#         msg = input("write msg: ")
#         proxy.proxy_sender(msg)
#         menu()

#     if option == "w":
#         time.sleep(0.1)
#         menu()
#     if option == "e":
#         print("exiting")


if __name__ == "__main__":
    
    listen = threading.Thread(target=proxy.proxy_listener)
    sender = threading.Thread(target=proxy.proxy_sender)
    listen.start()
    proxy.keySender()
    sender.start()

    listen.join()
    sender.join()


    

        

