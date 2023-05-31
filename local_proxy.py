from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import socket
import threading
import subprocess
import random
import json
from queue import Queue
from sympy import isprime
import pyDes
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from selenium import webdriver

# Create a thread-safe queue
url_queue = Queue()
queue_condition = threading.Condition()
port = int(input("port : "))
conn_ip = "192.168.206.1" #input("connection_ip : ")

def open_web_browser(url_queue, queue_condition):
    global urls
    print("Opening browser...")
    # Create a WebDriver instance (assuming you have the appropriate driver executable)
    driver = webdriver.Chrome()

    # Initially just open a new tab
    driver.get('about:blank')

    time.sleep(15)  # wait for some time
    while True:
        print("Current URL: ", driver.current_url)
        with queue_condition:
            # Append the item to the queue
            url_queue.put(driver.current_url)
            # Notify other threads that the queue has been updated
            queue_condition.notify_all()
        # Now navigate to the HTML file
        time.sleep(2)  # wait for some time
        #driver.get('http://localhost:8000')  # this should be your local server address


    # Close the WebDriver
    driver.quit()


# # Create webdriver object
# options = Options()
# # Use an existing Chrome instance
# options.add_argument("--remote-debugging-port=9222")
# driver = webdriver.Chrome(options=options)
# prev = driver.current_url

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
        self.file_name = 0
        
        #self.driver = webdriver.Chrome()
        
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
    def proxy_sender(self, url_queue, queue_condition): 
        while True:
            try: 
                with queue_condition:
            # Wait for the queue to have items
                    while url_queue.empty():
                        queue_condition.wait()
                # if not url_queue.empty():              
                    #print("-------------------------------------------------")                              
                    sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sender.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sender.connect((self.conn_ip,self.PORT))
                    # Retrieve the website URL from the active Chrome browser
                    
                    website_url = url_queue.get() 
                    print("website url : -------------------- ", website_url)
                    # Create the request dictionary
                    request = {
                        #"myIP": "...",
                        "website": website_url
                    }
                    # encryt the request
                    encrypted_msg = self.encrypt_message(request)
                    sender.send(encrypted_msg)
                    sender.close()
                # else:
                #     time.sleep(1)  
            except socket.error as e:
                pass
                #print("sender error: ", e)

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


    def proxy_listener(self): 
        while(True):
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client.bind(("", self.PORT))
            client.listen()
            s, address = client.accept()
            MAX_BUFFER_SIZE = 1048576  # Maximum buffer size per recv() call

            msg = b""  # Initialize an empty byte string to store the received data

            while True:
                chunk = s.recv(MAX_BUFFER_SIZE)  # Receive a chunk of data
                if not chunk:  # If the received chunk is empty, it indicates the end of the message
                    break
                msg += chunk  # Append the chunk to the received data         
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
                recovered_msg = decrypted_response.decode() # str type
               
                json_recovered_msg = json.loads(recovered_msg) # converted to json format
                # Process the decrypted response
                self.write_html_content(json_recovered_msg['website'])



    # write coming html content to file
    def write_html_content(self, content):
        global file_name
        with open('temp1.html', 'w', encoding='utf-8') as file:
            file.write(content)
        

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
    
class MyHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/temp1.html'  # your html file
        return SimpleHTTPRequestHandler.do_GET(self)

# Define the server
server = HTTPServer(('localhost', 8000), MyHandler)

def run_server():
    print('Starting server...')
    server.serve_forever()



proxy = Local_Proxy()

# Create the queue
url_queue = Queue()

if __name__ == "__main__":
    
    listen = threading.Thread(target=proxy.proxy_listener)
    sender = threading.Thread(target=proxy.proxy_sender, args=(url_queue, queue_condition))
    server_thread = threading.Thread(target=run_server)
    open_browser = threading.Thread(target=open_web_browser, args=(url_queue, queue_condition))

    listen.start()
    proxy.keySender()
    server_thread.start()
    open_browser.start()
    sender.start()

    listen.join()
    sender.join()
    server_thread.join()
    open_browser.join()

    

        

