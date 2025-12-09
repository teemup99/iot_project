from machine import Pin
import time
import network
import socket

# --- PIR + LED ---
pir = Pin(0, Pin.IN, Pin.PULL_DOWN)
led = Pin(2, Pin.OUT)

counter = 0
pir_state = False
last_motion = 0
debounce = 0.5

# --- WiFi ---
SSID = "wifi314too"
PASSWORD = "220473-314"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)

while wlan.status() != 3:
    print("Connecting...")
    time.sleep(1)

ip = wlan.ifconfig()[0]
print("Connected:", ip)

# --- HTML page (optional) ---
def generate_html():
    return """<html><body><h1>Pico Counter</h1></body></html>"""

# --- Server ---
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', 80))
s.listen(1)
print("Listening on port 80")

while True:
    # PIR detection
    val = pir.value()
    now = time.time()

    if val == 1 and not pir_state and now - last_motion > debounce:
        pir_state = True
        counter += 1
        last_motion = now
        led.on()
        print("Motion:", counter)

    if val == 0 and pir_state and now - last_motion > debounce:
        pir_state = False
        last_motion = now
        led.off()

    # Connection handler
    try:
        cl, addr = s.accept()
        #print("Client connected:", addr)

        request = cl.recv(512).decode()

        if "GET /count" in request:
            cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n")
            cl.send(str(counter))
            cl.close()
            continue

        # Serve normal page
        cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
        cl.send(generate_html())
        cl.close()

    except OSError:
        pass

    time.sleep(0.01)