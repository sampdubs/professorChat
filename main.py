from flask import Flask, render_template
import eventlet, socketio, smtplib, imaplib, email
from json import load
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header

from threading import Thread, Event
import time

eventlet.monkey_patch()

class Listener(Thread):
    def __init__(self, username, password, sio):
        super().__init__()
        self.username = username
        self.password = password
        self.stop_event = Event()
        self.sio = sio

    def checkForEmail(self):
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(self.username, self.password)
        res, count = imap.select('inbox')
        print(queue)
        if int(count[0]):
            print("Recieved email!")
            res, msg = imap.fetch("1", "(RFC822)")
            msg = msg[0][1].decode()
            content_beginning = "Content-Location: text_0.txt\r\n\r\n"
            content_end = "\r\n--__CONTENT"
            content_index = msg.find(content_beginning)
            content = msg[content_index + len(content_beginning) : msg[content_index:].find(content_end) + content_index]
            imap.store(b"1", '+FLAGS', '\\Deleted')
            imap.expunge()
            imap.close()
            imap.logout()
            return content
        return False


    def forwardMessage(self, message):
        if queue:
            respondingTo = queue[0]
            sendResponse(message, room=respondingTo[0])
            print("Emitted message", message, "to", respondingTo)
            if len(queue) > 1:
                queue.pop(0)
                sendQuestion(queue[0][1])

    def run(self):
        while not self.stop_event.wait(1):
            content = self.checkForEmail()
            if content:
                self.forwardMessage(content)

    def stop(self):
        self.stop_event.set()
    
PHONE_NUMBERS = {
    "PRAUS": "2023095568@vtext.com",
    "SAM": "6782451345@vtext.com"
}

server = smtplib.SMTP("smtp.gmail.com", 587)
server.ehlo()
server.starttls()
cred = load(open("config.json"))
server.login(cred["username"], cred["password"])

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
sio = socketio.Server()
listener = Listener(cred["username"], cred["password"], sio)

queue = []

@app.route("/")
def enterCode():
    return render_template("enterCode.html")

@app.route("/<code>")
def startSession(code):
    if code in PHONE_NUMBERS:
        return render_template("session.html", code=code)
    return render_template("badCode.html", code=code)

def sendResponse(message, room=None):
    sio.emit("resp", {"message": message}, room=room)

def sendQuestion(message):
    server.sendmail("chatwithprofessor@gmail.com", "6782451345@vtext.com", message)

@sio.on("question")
def sendText(sid, json, methods=["GET", "POST"]):
    print("Recieved Qestion from", sid, "Content:", json["message"])
    if not queue:
        sendQuestion(json["message"])
    elif queue[0][0] == sid:
        sendQuestion(json["message"])
        return
    queue.append((sid, json["message"]))


if __name__ == "__main__":
    listener.start()
    app = socketio.Middleware(sio, app)
    eventlet.wsgi.server(eventlet.listen(('', 8080)), app)