from flask import Flask, render_template, request
from json import load
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from flask_socketio import SocketIO

PHONE_NUMBERS = {
    "PRAUS": "+12023095568",
    "SAM": "+16782451345"
}

cred = load(open("config.json"))
client = Client(cred["account_sid"], cred["auth_token"])

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
sio =  SocketIO(app)

queue = []
sidToCode = {}

@app.route("/", methods=['GET', 'POST'])
def enterCode():
    return render_template("enterCode.html")

@app.route("/<code>", methods=['GET', 'POST'])
def startSession(code):
    if code in PHONE_NUMBERS:
        return render_template("session.html", code=code)
    return render_template("badCode.html", code=code)

@app.route("/sms_response", methods=['GET', 'POST'])
def smsResponse():
    if queue:
        respondingTo = queue[0]
        message = request.values.get('Body', None)
        sendResponse(message, room=respondingTo[0])
        print("Emitted message", message, "to", respondingTo)
        if len(queue) > 1:
            queue.pop(0)
            sendQuestion(sidToCode[queue[0][0]], queue[0][1])
    return str(MessagingResponse())

def sendResponse(message, room=None):
    sio.emit("resp", {"message": message}, room=room)

def sendQuestion(numberCode, message):
    message = client.messages.create(
        body=message,
        from_="+17253732428",
        to=PHONE_NUMBERS[numberCode])

@sio.on("whichProf")
def saveCode(json, methods=["GET", "POST"]):
    sidToCode[request.sid] = json["code"]

@sio.on("question")
def sendText(json, methods=["GET", "POST"]):
    sid = request.sid
    print("Recieved Qestion from", sid, "Content:", json["message"])
    if not queue:
        sendQuestion(sidToCode[sid], json["message"])
    elif queue[0][0] == sid:
        sendQuestion(sidToCode[sid], json["message"])
        return
    queue.append((sid, json["message"]))


if __name__ == "__main__":
    sio.run(app, debug=True)