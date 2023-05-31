
import socket
import threading
import time
import random
import json
from pyDes import triple_des, PAD_PKCS5
import copy
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, urlencode, parse_qs

chromedriver = "/home/airbenders/Downloads/chromedriver_linux64/chromedriver"
options = Options()
options.binary_location = '/usr/bin/google-chrome-stable'
# Use an existing Chrome instance
options.add_argument("--remote-debugging-port=9222")
driver1 = webdriver.Chrome(chromedriver, options=options)

port = int(input("Port : "))

class EC2_Proxy():
    def __init__(self):
        self.PORT = port
        self.bit_length_key = 6
        self.B = 0
        self.key = ""
        self.local_ip = ""
        self.is_key_exchange_completed = False
        self.send_search_result = ""
        self.send_message = False
        
    def listener(self): 
        while(True):
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client.bind(("", self.PORT))
            client.listen()
            s, address = client.accept()
            self.local_ip = address[0]
            msg = s.recv(1024*1024)           
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

            else:
                if len(msg) > 0:
                    # Implement your decryption logic
                    # msg_padded = msg.ljust((len(msg)//8 + 1) * 8)
                    recovered_msg = self.decrypt_request(msg) # as bytes

                    # since recovered msg is type bytes, turn it as json format
                    decoded_recovered_msg = recovered_msg.decode()
                    json_format_recoverd_msg = json.loads(decoded_recovered_msg)

                    # Extract the website URL from the decrypted request

                    website_url = json_format_recoverd_msg['website']
                    print("coming url -----------------------------", website_url)
                    if website_url == "http://localhost:8000/":
                        continue
                    search_result = self.get_page_source(website_url)

                    # Encrypt the search result
                    search_result = {"website" : search_result}  

                    search_result_encrypted = self.encrypt_request(search_result)
                    self.send_search_result = search_result_encrypted # send this to local

                    #print(search_result)
                    self.send_message = True

                    time.sleep(0.1)
                
    
    def decrypt_request(self,encrypted_request):
        # Implement your decryption logic
        decrypted_request = triple_des(self.key.ljust(24)).decrypt(encrypted_request, padmode=PAD_PKCS5)
        return decrypted_request

    def encrypt_request(self,request):
        # Implement your encryption logic
        request_str = json.dumps(request)
        encrypted_request = triple_des(self.key.ljust(24)).encrypt(request_str, padmode=PAD_PKCS5)
        return encrypted_request
    
    def get_page_source(self,url):
        parsed_url = urlparse(url)
        if parsed_url.scheme and parsed_url.netloc:
            driver1.get(url)  # Complete URL, navigate to the page
        else:
            search_url = 'https://www.google.com/search?' + \
                urlencode({'q': url})
            driver1.get(search_url)  # Search query, perform a search on Google

        #print(driver1.page_source)
        return driver1.page_source


    def sender(self):
        while True:
            try:

                if  len(self.local_ip) > 0 and not self.is_key_exchange_completed:
                    key_msg = str({"type" : "key", "B" : f"{self.B}"}).replace("'", '"')
                    key_sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    key_sender.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 2)
                    key_sender.connect((self.local_ip,self.PORT))
                    key_sender.send(key_msg.encode())
                    key_sender.close()
                    self.is_key_exchange_completed = True
                    print("KEY EXCHANGE COMPLETED !!!!!!!!!!!!!")
                if self.is_key_exchange_completed:
                    if self.send_message:

                        send_msg = copy.deepcopy(self.send_search_result)
                        print("message sended   +++++++++++++++++++**********************************++")
                        sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sender.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 2)
                        sender.connect((self.local_ip, self.PORT))
                        sender.send(send_msg)
                        sender.close()
                        self.send_message = False
                        time.sleep(1)
            except socket.error as e:
                print("sender error: ", e)



if __name__ == "__main__":
    driver = webdriver.Chrome()
    proxy = EC2_Proxy()
    ec2_listener = threading.Thread(target=proxy.listener)
    ec2_sender = threading.Thread(target=proxy.sender)

    ec2_listener.start()
    ec2_sender.start()

    ec2_listener.join()
    ec2_sender.join()
    
        
    
