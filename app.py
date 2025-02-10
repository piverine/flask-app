from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Initialize Firebase Admin SDK
cred = credentials.Certificate("path/to/your-firebase-adminsdk.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route("/register", methods=["POST"])
def register_user():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    try:
        user = auth.create_user(email=email, password=password)
        db.collection("users").document(user.uid).set({"email": email})
        return jsonify({"message": "User registered successfully", "uid": user.uid})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/login", methods=["POST"])
def login_user():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    try:
        user = auth.get_user_by_email(email)
        return jsonify({"message": "Login successful", "uid": user.uid})
    except Exception:
        return jsonify({"error": "Invalid credentials or user does not exist"}), 401

@app.route("/events", methods=["POST"])
def create_event():
    data = request.json
    event_id = db.collection("events").document().id
    data["id"] = event_id
    db.collection("events").document(event_id).set(data)
    return jsonify({"message": "Event created successfully", "id": event_id})

@app.route("/events", methods=["GET"])
def get_events():
    events = [doc.to_dict() for doc in db.collection("events").stream()]
    return jsonify(events)

@app.route("/register_event", methods=["POST"])
def register_event():
    data = request.json
    user_id = data.get("user_id")
    event_id = data.get("event_id")
    
    if not user_id or not event_id:
        return jsonify({"error": "User ID and Event ID are required"}), 400
    
    db.collection("registrations").add({"user_id": user_id, "event_id": event_id})
    return jsonify({"message": "User registered for event"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
