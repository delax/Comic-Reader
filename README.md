# Comic-Reader
A simple web server to display files.
Personally, I use it to serve comics from my desktop to read on my phone.

## To Use
1. `python reader.py "C:\directory\to\start\at"`
2. Make sure server and clients are on the same network
3. Find the *Local* ip address of the serving computer, on the same network the clients will be on. [This site](https://www.whatismybrowser.com/detect/what-is-my-local-ip-address) may help
4. On the client device, open the ip address at port 8080 (ex: http://10.0.0.1:8080/ but replace 10.0.0.1 with your ip)

One way to test it is working on the server computer, is to open [http://localhost:8080/](http://localhost:8080/) on the server's browser.
