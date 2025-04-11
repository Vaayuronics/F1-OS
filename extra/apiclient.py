import requests
import time
import network
import os
from dynamicResponse import DynamicResponse
from main import setLED
from machine import reset

ssid = "utexas-iot"
password = "17981954548150055250"
#ip = "128.62.67.220" #Utexas wifi global ip of computer
#ip = "10.57.205.213" #Local ip of computer
ip = "57.132.171.87" #Home ip global -> rpi

class Client:

    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.connect_wifi()
        self.machineID = self.__find_ID()

    def connect_wifi(self) -> None:
        """Connect to wifi"""
        setLED(True)
        self.wlan.active(True)
        self.wlan.connect(ssid, password)

        self.ip = self.wlan.ifconfig()[0]

        # Wait until connected
        counter = 0
        while not self.wlan.isconnected():
            if(counter == 30):
                reset()
            counter += 1
            self.pico.displayText(f"Connecting {counter}", 0, 0)
            time.sleep(1)
        
        print("Connected to WiFi", self.wlan.ifconfig())
        setLED(False)

    def is_connected(self) -> bool:
        """Returns whether connected to wifi or not"""
        return self.wlan.isconnected()

    def __create_machine(self) -> int:
        """Sends a request to create a new machine row and returns the id"""
        data = {
            'version' : self.VERSION,
            'ip' : self.ip
        }
        return int(self.__post("/machines/", data).get('id'))

    def __get(self, request) -> DynamicResponse:
        """Returns a JSON formatted dictionary of a get request"""
        if not self.is_connected():
            self.connect_wifi()
        elif request == None:
            raise Exception("Request must not be null")
        
        self.pico.setLED(True)

        try:
            url = f"http://{ip}:7106{request}"
            response = requests.get(url)
            dynResponse = DynamicResponse(response.json(), response.status_code)         
            response.close()  # Close the response object
            self.pico.setLED(False)
            return dynResponse
        except Exception as e:
            print("Error:", str(e))
            self.pico.setLED(False)
            return DynamicResponse({'detail' : str(e)}, -1)

    def __set(self, request) -> DynamicResponse:
        """Returns a JSON formatted dictionary of a put request"""
        if not self.is_connected():
            self.connect_wifi()
        elif request == None:
            raise Exception("Request must not be null")

        self.pico.setLED(True)

        try:
            url = f"http://{ip}:7106{request}"
            response = requests.put(url)
            dynResponse = DynamicResponse(response.json(), response.status_code)         
            response.close()  # Close the response object
            self.pico.setLED(False)
            return dynResponse
        except Exception as e:
            print("Error:", str(e))
            self.pico.setLED(False)
            return DynamicResponse({'Error' : str(e)}, -1)

    def __post(self, request, data) -> DynamicResponse:
        """Returns a JSON formatted dictionary"""
        if not self.is_connected():
            self.connect_wifi()
        elif request == None:
            raise Exception("Request must not be null")
        
        self.pico.setLED(True)

        try:
            url = f"http://{ip}:7106{request}"
            response = requests.post(url, json=data)
            dynResponse = DynamicResponse(response.json(), response.status_code)         
            response.close()  # Close the response object
            self.pico.setLED(False)
            return dynResponse
        except Exception as e:
            print("Error:", str(e))
            self.pico.setLED(False)
            return DynamicResponse({'detail' : str(e)}, -1)

    def get_software_update(self) -> DynamicResponse:
        """Gets the latest update data and returns it as a dynamic response object"""
        return self.__get(f"/updates/latest")

    def file_exists(self, filepath) -> bool:
        """Returns if a file exists or not using the os.stat method"""
        try:
            os.stat(filepath)
            return True
        except OSError:
            return False