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

account_sid = os.environ.get('TWILIO_SID', "")
auth_token = os.environ.get('AUTH_TOKEN', "")
client = Client(account_sid, auth_token)

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
    message = request.values.get('Body', None)
    from_number = request.values.get('From', None)
    print("QUEUE:", queue)
    if queue:
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
        print("QUEUE:", queue)
    return str(MessagingResponse())

def sendResponse(message, room=None):
    sio.emit("resp", {"message": message}, room=room)

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
    if not queue:
        sendQuestion(sidToCode[sid], json["message"])
    elif queue[0][0] == sid:
        sendQuestion(sidToCode[sid], json["message"])
        return
    queue.append((sid, json["message"]))
    print("QUEUE:", queue)

if __name__ == "__main__":
    sio.run(app, debug=True, host="0.0.0.0", port=int(os.environ.get('PORT')))