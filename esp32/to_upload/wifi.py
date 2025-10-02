import time
import network

# Local application/library-specific imports
from utils import print_log

MAX_CONNECTION_ATTEMPTS = 10

class WIFI_handler:
    def __init__(self):
        self.check_wifi_credentials()
        self.setup_wifi()


    def check_wifi_credentials(self):
        """
        Check if WiFi credentials are available from a file 

        :return: Tuple[str, str] - The SSID and password retrieved or configured
        """
        self.ssid, self.password = "", ""

        with open('wifi_creds.txt', 'r') as f:
            self.ssid, self.password = f.read().split(',')

        print_log('Wifi credentials found')

        #return ssid, password
    

    def setup_wifi(self):
        """
        Connect to a WiFi network using provided credentials.
        Initializes self.wlan
        """

        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)

        try:
            self.wlan.connect(self.ssid, self.password)
        except Exception as exc:
            print_log(f"Could not connect to WiFi network", error=True, exc=exc)
            raise

        # Give WiFi 30 seconds to connect
        start_time = time.time()
        while not self.isconnected():
            if time.time() - start_time > 30:  # After 30 seconds
                break
            time.sleep(0.1)
        
        print_log(f'connected: {self.isconnected()} after {time.time() - start_time}s')


    def isconnected(self):
        return self.wlan.isconnected()
    

    def try_connect(self):
        '''
        Tries to connect to the wifi for 30s, than waits for 10s.
        This for up to 10 times, total 400s.
        '''
        attempts = 0
        while attempts < MAX_CONNECTION_ATTEMPTS:
            attempts += 1

            if not self.isconnected():
                # Log WLAN Reconnect Attempt
                print_log('WLAN not connected, trying to reconnect.')

                try:
                    self.setup_wifi()
                except Exception as exc:
                    print_log(f"Error trying to reconnect", error=True, exc=exc)
                    raise
            else:
                break
            
            # Try again afte 10s
            time.sleep(10) 
        else: 
            raise TimeoutError('Unable to connect to the wifi')