from machine import Pin
import ntptime
import time
import network
import urequests
import socket
import config
import ssl
from umqtt.simple import MQTTClient

# PIR + LED setup
pir = Pin(0, Pin.IN, Pin.PULL_DOWN)
led = Pin(2, Pin.OUT)

counter = 0
pir_state = False
last_motion = 0
debounce = 0.5
valkkumisvali = 0
houradjust = 2


def blink(times=5, delay=0.1):
    for _ in range(times):
        led.on(); time.sleep(delay)
        led.off(); time.sleep(delay)

# WiFi setup
SSID = config.ssid
PASSWORD = config.pwd

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)

while wlan.status() != 3:
    #print("Connecting...")
    time.sleep(1)

ip = wlan.ifconfig()[0]
#print("Connected:", ip)
blink(3, 0.1)

# HTML
def generate_html():
    return """<html><body><h1>Pico Counter</h1></body></html>"""

#callback function
def my_callback(topic, message):
    global valkkumisvali
    splitted = str(message).split("\'")
    valkkumisvali = int(splitted[1])
    return

def convert_time():
    tm = time.localtime()
    correct_time = time.localtime(time.mktime(tm) + houradjust * 3600)
    return "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(
        correct_time[0], correct_time[1], correct_time[2], #mmddyyy
        correct_time[3], correct_time[4], correct_time[5] #hhmmss
        )

def send_to_db(datetime):
    encoded_datetime = datetime.replace(" ", "%20")
    url = "{}?date={}".format(config.sheet_url, encoded_datetime)
    response = urequests.get(url)
    #print("Data sent")
    return

#time_sync
ntptime.host = "time.google.com"
ntptime.settime()
#print(time.localtime())

# Server setup
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', 80))
s.listen(1)
#print("Listening on port 80")

# MQTT Setup

# config ssl connection w Transport Layer Security encryption (no cert)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT) # TLS_CLIENT = connect as client not server/broker
context.verify_mode = ssl.CERT_NONE # CERT_NONE = not verify server/broker cert - CERT_REQUIRED: verify

client = MQTTClient(
                    client_id=b'motionsensor',
                    server=config.MQTT_BROKER,
                    port=config.MQTT_PORT,
                    user=config.MQTT_USER,
                    password=config.MQTT_PWD,
                    ssl=True,
                    ssl_params={
                        "server_hostname": config.MQTT_BROKER
                        }
                    )
client.set_callback(my_callback)

client.connect()
client.subscribe("change")

while True:
    # PIR detection
    val = pir.value()
    now = time.time()

    if val == 1 and not pir_state and now - last_motion > debounce:
        pir_state = True
        counter += 1
        last_motion = now
        if valkkumisvali > 0 and (counter % valkkumisvali == 0):
            blink()
        client.publish("counter", str(counter))
        send_to_db(convert_time())

    if val == 0 and pir_state and now - last_motion > debounce:
        pir_state = False
        last_motion = now
        led.off()
        
    client.check_msg()
    
    time.sleep(0.01)