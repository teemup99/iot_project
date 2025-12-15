from machine import Pin
import time
import network
import socket

# PIR + LED setup
pir = Pin(0, Pin.IN, Pin.PULL_DOWN)
led = Pin(2, Pin.OUT)

counter = 0
pir_state = False
last_motion = 0
debounce = 0.5
valkkumisvali = 0

def blink(times=5, delay=0.1):
    for _ in range(times):
        led.on(); time.sleep(delay)
        led.off(); time.sleep(delay)

# WiFi setup
SSID = "OTiT"
PASSWORD = "oh8taoh8ta"

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

# Server setup
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', 80))
s.listen(1)
#print("Listening on port 80")

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
        #print("Motion:", counter)

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
        
        # Handle GET /setblink?value=N
        if "GET /setblink" in request:
            try:
                # Extract number after ?value=
                part = request.split("value=")[1]
                newval = int(part.split()[0])
                valkkumisvali = newval
                #print("Blink interval updated to:", valkkumisvali)

                cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n")
                cl.send("OK")
                cl.close()
                continue
            except:
                cl.send("HTTP/1.1 400 Bad Request\r\n\r\n")
                cl.close()
                continue

        # Serve normal page
        cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
        cl.send(generate_html())
        cl.close()

    except OSError:
        pass

    time.sleep(0.01)