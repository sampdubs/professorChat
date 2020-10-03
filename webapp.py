from flask import Flask, render_template, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from flask_socketio import SocketIO
import os

PHONE_NUMBERS = {
    "PRAUS": "+12023095567",
    "BRETT": "+16172302319",
    "SAM": "+16782451345"
}

REVERSE_PHONE_NUMBERS = {
    "+12023095567": "PRAUS",
    "+16172302319": "BRETT",
    "+16782451345": "SAM"
}

account_sid = os.environ.get('TWILIO_SID', "")
auth_token = os.environ.get('AUTH_TOKEN', "")
client = Client(account_sid, auth_token)

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
sio =  SocketIO(app)

queues = {code: [] for code in PHONE_NUMBERS}
sidToCode = {}
alreadyResponded = {code: False for code in PHONE_NUMBERS}

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
    message = request.values.get('Body', None)
    code = REVERSE_PHONE_NUMBERS[request.values.get('From', None)]
    queue = queues[code]
    print("QUEUE:", queue)
    if queue:
        if message.startswith("*"):
            if message.startswith("**"):
                sendResponse(message.lstrip("*"), special=True)
                return str(MessagingResponse())

            for sid in sidToCode:
                if code == sidToCode[sid]:
                    sendResponse(message.lstrip("*"), room=sid, special=True)
            return str(MessagingResponse())

        global alreadyResponded
        alreadyResponded[code] = True
        respondingTo = queue[0]
        sendResponse(message, room=respondingTo[0])
        print("Emitted message", message, "to", respondingTo)
        if len(queue) > 1:
            queue.pop(0)
            sending = [(sidToCode[queue[0][0]], queue[0][1])]
            for i in range(len(queue) - 1, 0, -1):
                if queue[i][0] == queue[0][0]:
                    query = queue.pop(i)
                    sending.append((sidToCode[query[0]], query[1]))
            for outMessage in sending:
                sendQuestion(*outMessage)
            alreadyResponded[code] = False
        print("QUEUE:", queue)
    return str(MessagingResponse())

def sendResponse(message, room=None, special=False):
    sio.emit("resp", {"message": message, "special": special}, room=room)

def sendQuestion(numberCode, message):
    client.messages.create(
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
    global alreadyResponded
    code = sidToCode[sid]
    queue = queues[code]
    if not queue:
        sendQuestion(code, json["message"])
    elif queue[0][0] == sid:
        sendQuestion(code, json["message"])
        alreadyResponded[code] = False
        return
    elif alreadyResponded[code]:
        sendQuestion(code, json["message"])
        queue.pop(0)
    alreadyResponded[code] = False
    queue.append((sid, json["message"]))
    print("QUEUE:", queue)

if __name__ == "__main__":
    sio.run(app, debug=True, host="0.0.0.0", port=int(os.environ.get('PORT')))