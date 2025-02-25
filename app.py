# from flask import Flask, render_template, request, redirect, url_for, session
# from flask_socketio import SocketIO, join_room, leave_room, send
# import random
# import string

# app = Flask(__name__)
# app.secret_key = "your_secret_key"
# socketio = SocketIO(app, cors_allowed_origins="*")  # Enable cross-device communication

# # Store active chat sessions
# active_sessions = {}

# def generate_unique_code():
#     return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
 
# @app.route("/")
# def home():
#     return render_template("home.html")

# @app.route("/create_session", methods=["POST"])
# def create_session():
#     unique_code = generate_unique_code()
#     session["code"] = unique_code
#     active_sessions[unique_code] = {"users": []}
#     return render_template("share_code.html", code=unique_code)

# @app.route("/join", methods=["POST"])
# def join_session():
#     code = request.form.get("code")
#     if code in active_sessions:
#         return redirect(url_for("chat", code=code))
#     return "Invalid Code. Try Again."

# @app.route("/chat/<code>")
# def chat(code):
#     if code not in active_sessions:
#         return "Invalid or expired session."
#     session["code"] = code
#     return render_template("chat.html", code=code)

# @socketio.on("join")
# def handle_join(data):
#     room = data["code"]
#     join_room(room)
#     send(f"A user joined the chat.", room=room)

# @socketio.on("message")
# def handle_message(data):
#     room = data["code"]
#     send(data["message"], room=room)

# if __name__ == "__main__":
#     socketio.run(app, host="192.168.183.102", port=5000, debug=True)
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, send
import random
import string

app = Flask(__name__)
app.secret_key = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active chat rooms
chat_rooms = {}

def generate_unique_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/create_chat", methods=["POST"])
def create_chat():
    code = generate_unique_code()
    chat_rooms[code] = {"users": []}  # Store active rooms
    session["code"] = code
    return render_template("waiting_room.html", code=code)

@app.route("/join_chat", methods=["POST"])
def join_chat():
    code = request.form.get("code").strip()
    if code in chat_rooms:
        return redirect(url_for("chat", code=code))
    return "Invalid Code!"

@app.route("/chat/<code>")
def chat(code):
    if code not in chat_rooms:
        return "Invalid Code!"
    session["code"] = code
    return render_template("chat.html", code=code)

@socketio.on("join")
def handle_join(data):
    room = data["code"]
    join_room(room)

    if "users" in chat_rooms[room] and len(chat_rooms[room]["users"]) < 2:
        chat_rooms[room]["users"].append(request.sid)
    
    if len(chat_rooms[room]["users"]) == 2:
        socketio.emit("redirect_to_chat", {"code": room}, room=room)

@socketio.on("message")
def handle_message(data):
    room = data["code"]
    send(data["message"], room=room)

if __name__ == "__main__":
    socketio.run(app, host="192.168.183.102", port=5000, debug=True)
