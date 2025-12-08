from machine import Pin
import time
import network
import socket

# --- PIR + LED setup ---
pir = Pin(0, Pin.IN, Pin.PULL_DOWN)
led = Pin(2, Pin.OUT)
pir_state = False
last_motion_time = 0
debounce_time = 0.5
counter = 0

def blink_led(times=2, delay=0.2):
    for _ in range(times):
        led.on()
        time.sleep(delay)
        led.off()
        time.sleep(delay)

print("PIR Module Initialized")
time.sleep(1)
print("Ready")

# --- WiFi setup ---
SSID = "iPhone (Leon)"       # change to your hotspot
PASSWORD = "munakokkeli"     # change to your hotspot password

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)
while wlan.status() != 3:
    print("Connecting to Wi-Fi...")
    time.sleep(1)

ip = wlan.ifconfig()[0]
print("Connected! Pico W IP Address:", ip)
blink_led(3, 0.1)

# --- HTML page ---
def generate_html():
    return """<!DOCTYPE html>
<html>
<head>
<title>Pico W Motion Sensor</title>
<script>
var evtSource = new EventSource("/stream");
evtSource.onmessage = function(e) {
    document.getElementById("count").innerText = e.data;
};
</script>
</head>
<body>
<h1>People detected:</h1>
<h2 id="count">0</h2>
</body>
</html>"""

#closes the socket if it was in use
try:
    s.close()
except:
    pass

# --- Socket server setup ---
addr = ('0.0.0.0', 80)
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(1)
s.settimeout(0.1)  # non-blocking accept
print("Listening on", addr)

# --- SSE clients list ---
clients = []

# --- Main loop ---
while True:
    # --- PIR detection ---
    val = pir.value()
    current_time = time.time()
    if val == 1:
        if not pir_state and (current_time - last_motion_time >= debounce_time):
            pir_state = True
            led.on()
            counter += 1
            last_motion_time = current_time
            print("Motion detected! Count:", counter)
    else:
        if pir_state and (current_time - last_motion_time >= debounce_time):
            pir_state = False
            led.off()
            last_motion_time = current_time

    # --- Accept new clients ---
    try:
        cl, addr = s.accept()
        request = cl.recv(1024).decode()
        # Blink LED to indicate a new client connection
        blink_led(2, 0.1)
        if "GET /stream" in request:
            # SSE client
            cl.send("HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/event-stream\r\n"
                    "Cache-Control: no-cache\r\n"
                    "Connection: keep-alive\r\n\r\n".encode())
            time.sleep(0.05)
            clients.append(cl)
            print("SSE client connected:", addr)
        else:
            # Serve HTML page
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n"
            response += generate_html()
            cl.send(response.encode())
            cl.close()
    except OSError:
        pass  # no client this loop

    # --- Send updates to SSE clients ---
    for c in clients[:]:  # iterate over a copy to safely remove clients
        try:
            c.send(f"data: {counter}\n\n".encode())
            time.sleep(0.01)  # small delay to flush TCP buffer
        except OSError:
            clients.remove(c)  # client disconnected
            print("client disconnected")

    time.sleep(0.05)  # main loop delay