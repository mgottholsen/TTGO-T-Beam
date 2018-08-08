# Getting u-blox MAX-7C GPS to work with Assisted A-GPS

So you got your u-blox GPS and wired it up only to look at it struggling to get a valid fix? Under less than ideal conditions, it can take a better part of half an hour. That's because unlike your smartphone GPS, it doesn't have the luxury of having downloaded all the auxiliary navigation data (almanacs and the lot) out-of-band, via fast mobile connection. Instead it relies on the satellite's signal itself, which is being transmitted to you at meager 50 bits per second (I'm not missing "kilo" there, it's three orders of magnitude slower than your 2G GPRS connection).

Luckily, the u-blox receivers are fitted with what the company calls "AssistNow" capability and it does exactly the same thing your iPhone does - feeds the GPS with pre-downloaded almanacs, speeding up the acquisition process to mere seconds.

In principle, the process looks easy enough - we just need to download the data, and then push them to the receiver. Sadly, the AssistNow documentation is hard to find and even then a tad lacking. But that's why you're reading this article, right? Let's get to business!

## U-blox A-GPS offerings

AssistNow comes in two flavors: Online and Offline. The difference isn't the method of delivery of data - u-blox won't be snail-mailing you the almanacs. Instead, it's all about the validity of the data: **Online** is good for only two hours, **Offline** can last for a month. That means you can get the data preloaded if you expect to be offline for the measurements, but can be online at some time before getting to the field.

Of course the Offline service comes at a cost. While the Online packages are weighing in at single kilobytes (and are therefore downloaded fast even on 2G infrastructure), the 35-day-valid Offline pack will set you back a hefty 125kB. Also the Online is stated to be faster - u-blox claims 1 second time-to-fix best-case-scenario, compared to 5 seconds for Offline.

From now on, I'll be focusing on the Online branch, but Offline should be pretty much analogous.

## Getting the data

### Setting up the free account

Here's the first hurdle: u-blox requires an account to download the data. The process is a little unconventional, but fast: you need to send an email to `agps-account@u-blox.com`. If you're shy, don't worry - it's an automated service, you don't need to write anything. Leave both the subject and the body unfilled and just send a completely blank email. Within a minute or two, you'll receive your login from `agps-server@u-blox.com`:

    Dear xxx@xxx.xx

    Thank you for using this AGPS Service from u-blox.

    You account has been created as follows:

       Username: "xxx@xxx.xx"
       Password: "xxx"

       Server:   agps.u-blox.com
                 DO NOT USE IP NUMBERS.
       Port:     46434
       Protocol: TCP or UDP

    Newly created accounts can take up to a few hours until active.

Note the username, password, server and port and let's finally get the data package.

### Downloading

Here comes the second hurdle, as the u-blox protocol is quite similar to, yet not compatible with HTTP. We'll therefore have to forgo the high-level Request libraries and go to bare sockets! Don't worry though, the most complicated thing is splitting the HTTP-like header and getting the body of the message.

As I'm using the Raspberry Pi, I'll be coding in Python. Other languages should be analogous, however.

#### The Connection

First, we need to connect to the u-blox server. We use the `Socket` package, which is included in Python by default.

```python
import socket
sock = socket.socket()
address = "agps.u-blox.com"
port = 46434
print "Connecting to u-blox"
sock.connect((address, port))
print "Connection established"
```

#### The Request

Now we need to send the actual request. It's a sequence of `name=value` pairs, separated with semicolons `;`. The required variables are as follows:

* `cmd`: the requested information. `full` in our case, as it's no use for us to download only ephemeris or only almanac.
* `user`: your username (email)
* `pwd`: your password, in plain text
* `lat`: approximate latitude of your device (i.e. center of the state or country you're in)
* `lon`: approximate longitude of your device
* `pacc`: accuracy of the lat/lon position, in meters. Optional, defaults to 300000 (300 kilometers)

With that sorted out, let's send the request and load it into `data` variable

```python
print "Sending the request"
sock.send("cmd=full;user=xxx@xxx.xx;pwd=xxx;lat=50.0;lon=14.3;pacc=10000")

data = ""
buffer = True;

while buffer:
    buffer = sock.recv(1024)
    if buffer:
        data += buffer
```

#### Parsing the received data

If you now `print` the `data`, you'll see something like this:

    u-blox a-gps server (c) 1997-2009 u-blox AG
    Content-Length: 2696
    Content-Type: application/ubx

    (binary data)

The binary is what we're after, so let's parse it out. It's separated from the header with two empty lines, so we'll find the first occurence of `\r\n\r\n` with `index` and then slice (substring) the data. Of course it would be more appropriate to parse the header and check for error codes, but hey, who ever does that?

```python
headerEndsAt = data.index("\r\n\r\n")
binaryStartsAt = headerEndsAt + 4 # length of the newline sequence
binary = data[binaryStartsAt:]
```

That's it - we finally have all the data we need. Now to send them to the receiver.

## Uploading the data to GPS

This is comparatively simple, with one gotcha - apparently, the GPS doesn't handle well when there is duplex (bi-directional) communication on the serial line. I'm not completely sure about it, but I think it works better when you first drain the buffer and only then send the AGPS data.

```python
import serial
ser = serial.Serial("/dev/ttyAMA0", 9600)
print "Waiting for free line"
drainer = True
while drainer:
    drainer = ser.inWaiting()
    ser.read(drainer)
```

With the pipes clean, send the that just like we received it.

```python
print "Writing AGPS data"
ser.write(binary)
print "Done"
```

Now let's check our success and read the GPS - we should see an almost instantaneous fix. Read the serial and print out every `GPGGA` NMEA message, until keyboard interrupt (`ctrl+c`) is sent.

```python
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
```

Ideally, our output should look like this:

    Connecting to u-blox
    Connection established
    Sending the request
    Waiting for free line
    Writing AGPS data
    Done
    $GPGGA,223734.00,,,,,0,03,3.64,,,,,,*57
    $GPGGA,223735.00,,,,,0,03,3.64,,,,,,*56
    $GPGGA,223736.00,,,,,0,04,3.16,,,,,,*57
    $GPGGA,223737.00,,,,,0,04,3.16,,,,,,*56
    $GPGGA,223738.00,,,,,0,04,3.16,,,,,,*59
    $GPGGA,223739.00,,,,,0,04,3.16,,,,,,*58
    $GPGGA,223740.00,50xx.xxxxx,N,014xx.xxxxx,E,1,04,3.16,345.1,M,44.5,M,,*53
    $GPGGA,223741.00,50xx.xxxxx,N,014xx.xxxxx,E,1,04,3.16,345.4,M,44.5,M,,*51
    $GPGGA,223742.00,50xx.xxxxx,N,014xx.xxxxx,E,1,04,3.16,346.2,M,44.5,M,,*50
    $GPGGA,223743.00,50xx.xxxxx,N,014xx.xxxxx,E,1,04,3.16,345.0,M,44.5,M,,*50
    $GPGGA,223744.00,50xx.xxxxx,N,014xx.xxxxx,E,1,04,3.16,344.4,M,44.5,M,,*59
    $GPGGA,223745.00,50xx.xxxxx,N,014xx.xxxxx,E,1,04,3.16,344.0,M,44.5,M,,*52
    $GPGGA,223746.00,50xx.xxxxx,N,014xx.xxxxx,E,1,04,3.16,344.3,M,44.5,M,,*5A
    $GPGGA,223747.00,50xx.xxxxx,N,014xx.xxxxx,E,1,04,3.16,344.2,M,44.5,M,,*59

As you can see, we were able to get from cold start to fix in only six seconds. If you aren't so lucky on your first run, try executing the file again. For reasons yet unknown, the data package doesn't always get received. If you need a more bulletproof solution, you might want to run the sending in a cycle and check for the `ACK` message - you can see an implementation [here](https://github.com/chrisstubbs93/PiCode/blob/master/ubx.py).

The complete source code is available in the next file in this Gist. If you come upon any mistakes, file an Issue or even send a Pull Request, they're all welcome!

Thanks for reading and enjoy your newly fast GPS :-)

# License (MIT)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# References:

1. [U-Blox AssistNow Application Note](http://people.openmoko.org/matt_hsu/ImplementationAssistNowServerAndClient(GPS.G4-SW-05017-C).pdf)
