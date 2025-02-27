from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, join_room, send, emit
import random
import string
import os
import base64
from gtts import gTTS  # Text to Speech
import speech_recognition as sr  # Speech to Text
from flask_cors import CORS
from io import BytesIO
from pydub import AudioSegment
import io
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
app.secret_key = "secret"
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5000", "http://your-ip-address"])
CORS(app)

UPLOAD_FOLDER = "static/audio/"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

chat_rooms = {}  # Stores active chatrooms and user preferences

def generate_unique_code():
    """Generate a unique 6-character code for each chat room."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route("/")
def index():
    """Landing page where user selects input & output modes."""
    return render_template("index.html")

@app.route("/create_chat", methods=["POST"])
def create_chat():
    """Creates a new chat room with user preferences."""
    code = generate_unique_code()
    input_method = request.form.get("input_methodc")
    output_method = request.form.get("output_methodc")

    chat_rooms[code] = {
        "users": [],
        "first_user": {"input": input_method, "output": output_method},
        "second_user": None,
        "messages": [],
    }
    return redirect(url_for("waiting_room", code=code))

@app.route("/waiting_room/<code>")
def waiting_room(code):
    """Waiting page until the second user joins."""
    if code not in chat_rooms:
        return "Invalid Code!"
    return render_template("waiting_room.html", code=code)

@app.route("/join_chat", methods=["POST"])
def join_chat():
    """Allows a second user to join an existing chat."""
    code = request.form.get("code").strip()
    input_method = request.form.get("input_methodj")
    output_method = request.form.get("output_methodj")

    if code in chat_rooms and chat_rooms[code]["second_user"] is None:
        chat_rooms[code]["second_user"] = {"input": input_method, "output": output_method}
        socketio.emit("redirect_to_chat", {"code": code}, room=code)
        return redirect(url_for("chat", code=code))

    return "Invalid Code or Chat Already Full!"

@app.route("/chat/<code>")
def chat(code):
    """Renders the chatroom with correct settings."""
    if code not in chat_rooms:
        return "Invalid Code!"

    session["code"] = code
    user_count = len(chat_rooms[code]["users"])

    # Set user preferences correctly
    if user_count == 0:
        session["user_type"] = "first_user"
        user_settings = chat_rooms[code]["first_user"]
    else:
        session["user_type"] = "second_user"
        if chat_rooms[code]["second_user"] is None:
            chat_rooms[code]["second_user"] = {"input": "text", "output": "text"}
        user_settings = chat_rooms[code]["second_user"]

    return render_template(
        "chat.html",
        code=code,
        user_input=user_settings["input"],
        user_output=user_settings["output"],
    )

def save_audio_file(audio_base64):
    """Save base64 audio to a file and return its path."""
    try:
        audio_data = base64.b64decode(audio_base64)
        file_name = f"{random.randint(1000, 9999)}.mp3"
        file_path = os.path.join(UPLOAD_FOLDER, file_name)

        with open(file_path, "wb") as f:
            f.write(audio_data)

        return f"/static/audio/{file_name}"
    except Exception as e:
        print("Audio Save Error:", e)
        return ""


@socketio.on("join")
def handle_join(data):
    """Handles users joining the chat room."""
    room = data["code"]
    join_room(room)
    chat_rooms[room]["users"].append(request.sid)

    if len(chat_rooms[room]["users"]) == 2:
        socketio.emit("redirect_to_chat", {"code": room}, room=room)


@socketio.on("message")
def handle_message(data):
    """Handle messages and convert if needed."""
    room = data["code"]
    sender = request.sid
    message = data["message"]

    sender_type = "first_user" if sender == chat_rooms[room]["users"][0] else "second_user"
    receiver_type = "second_user" if sender_type == "first_user" else "first_user"

    sender_data = chat_rooms[room][sender_type]
    receiver_data = chat_rooms[room][receiver_type]

    response_data = {"message": message, "type": data.get("type", "text")}

    if sender_data["input"] == "voice" and receiver_data["output"] == "text":
        response_data["message"] = voice_to_text(message)  # Convert to text
        response_data["type"] = "text"

    elif sender_data["input"] == "text" and receiver_data["output"] == "voice":
        audio_path = text_to_voice(message)  # Convert to voice
        response_data["message"] = audio_path  # Send as file URL
        response_data["type"] = "audio"

    elif sender_data["input"] == "voice" and receiver_data["output"] == "voice":
        audio_path = save_audio_file(message)  # Store audio file
        response_data["message"] = audio_path  # Send as file URL
        response_data["type"] = "audio"

    send(response_data, room=room)

    chat_rooms[room]["messages"].append({"sender": sender, "message": message})


def voice_to_text(audio_base64):
    """Convert base64 audio to text."""
    try:
        audio_data = base64.b64decode(audio_base64)

        # Convert MP3 to WAV for speech recognition
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
        wav_buffer = io.BytesIO()
        audio_segment.export(wav_buffer, format="wav")
        wav_buffer.seek(0)

        # Recognize speech
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_buffer) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio)
        return text

    except Exception as e:
        print("Voice to Text Error:", e)
        return f"Error: {str(e)}"



def text_to_voice(text):
    """Converts text to voice and saves as MP3."""
    try:
        file_name = f"{random.randint(1000, 9999)}.mp3"
        file_path = os.path.join(UPLOAD_FOLDER, file_name)

        tts = gTTS(text)
        tts.save(file_path)

        return f"/static/audio/{file_name}"
    except Exception as e:
        print("Text to Voice Error:", e)
        return ""


@app.route("/check_user_joined/<code>")
def check_user_joined(code):
    """Checks if a second user has joined."""
    return jsonify({"joined": code in chat_rooms and chat_rooms[code]["second_user"] is not None})


if __name__ == "__main__":
    socketio.run(app, host="192.168.183.102", port=5000, debug=True)
