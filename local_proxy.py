

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import socket
import threading
import subprocess
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
        # self.options = Options()
        # # Add any necessary options for Chrome
        # self.driver = webdriver.Chrome(options=self.options)

    def encrypt_message(self, request):
        request_str = json.dumps(request)
        encrypted_msg = pyDes.triple_des(self.key.ljust(24)).encrypt(request_str, padmode=2)
        return encrypted_msg

    # send messages to ec2
    # message should be string
    def proxy_sender(self): 
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
                # encryt the request
                encrypted_msg = self.encrypt_message(request)
                sender.send(encrypted_msg)
                sender.close()
            except socket.error as e:
                print("sender error: ", e)

    # get the required key for encryption
    def keySender(self): 
        try:          
            # A = g^a mod(p)  a is random
            A = pow(self.g,self.a) % self.p
            msg = str({"type" : "key", "g" : f"{self.g}", "p" : f"{self.p}", "A" : f"{A}"}).replace("'", '"')
            key_sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            key_sender.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 2)
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
                    self.key = str(key)
                    self.is_key_exchange_completed = True

            else:
                # msg that comes from ec2
                # msg_padded = msg.ljust((len(msg)//8 + 1) * 8)
                decrypted_response = self.decrypt_response(msg)
                recovered_msg = decrypted_response.decode()
                recovered_msg = json.loads(recovered_msg) # converted to json format
                # Process the decrypted response
                # ...

                # Open the website in Chrome browser on the local machine
                self.open_website_in_chrome(recovered_msg['website'])

    # Implement your decryption logic
    def decrypt_response(self,response):
        decrypted_response = pyDes.triple_des(self.key.ljust(24)).decrypt(response, padmode=pyDes.PAD_PKCS5)
        return decrypted_response # as bytes

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

if __name__ == "__main__":
    
    listen = threading.Thread(target=proxy.proxy_listener)
    sender = threading.Thread(target=proxy.proxy_sender)
    listen.start()
    proxy.keySender()
    sender.start()

    listen.join()
    sender.join()


    

        

