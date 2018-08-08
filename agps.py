import socket
import serial

sock = socket.socket()
address = "agps.u-blox.com"
port = 46434
print "Connecting to u-blox"
sock.connect((address, port))
print "Connection established"

print "Sending the request"
sock.send("cmd=full;user=xxx@xxx.xx;pwd=xxx;lat=50.0;lon=14.3;pacc=10000")

data = ""
buffer = True;

while buffer:
    buffer = sock.recv(1024)
    if buffer:
        data += buffer
    
headerEndsAt = data.index("\r\n\r\n")
binaryStartsAt = headerEndsAt + 4 # length of the newline sequence
binary = data[binaryStartsAt:]

ser = serial.Serial("/dev/ttyAMA0", 9600)
print "Waiting for free line"
drainer = True
while drainer:
    drainer = ser.inWaiting()
    ser.read(drainer)

print "Writing AGPS data"
ser.write(binary)
print "Done"

buffer = True
message = ""
try:
    while buffer:
        buffer = ser.read()
        if buffer == "$":
            if message.startswith("$GPGGA"):
                print message.strip()
            message = ""
        message = message + buffer
except KeyboardInterrupt:
    ser.close()
