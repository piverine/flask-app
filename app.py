from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- IMPORTANT: Replace with the path to your service account key ---
cred = credentials.Certificate("path/to/your-firebase-adminsdk.json")  # Download from Firebase Console
firebase_admin.initialize_app(cred)
db = firestore.client()

# --- Authentication (Token Verification) ---

def verify_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'No token provided'}), 401

        try:
            id_token = auth_header.split(" ")[1]  # Bearer <token>
            decoded_token = auth.verify_id_token(id_token)
            # Add uid to request object, so we can access inside view functions
            request.uid = decoded_token['uid']
            
        except Exception as e:
            print(e) # log error
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)
    return decorated_function


# --- Event Routes ---
@app.route("/events", methods=["POST"])
@verify_token
def create_event():
    try:
        data = request.json
        # Get user ID from decoded token
        organizer_id = request.uid
        data['organizerId'] = organizer_id

        event_id = db.collection("events").document().id
        data["id"] = event_id
        db.collection("events").document(event_id).set(data)
        return jsonify({"message": "Event created successfully", "id": event_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/events", methods=["GET"])
def get_events():
    try:
        events = [doc.to_dict() for doc in db.collection("events").stream()]
        return jsonify(events), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- User-Specific Event Routes ---

@app.route("/users/<uid>/events", methods=["GET"])
@verify_token
def get_user_events(uid):
    try:
        if request.uid != uid: #added check to ensure user is authorised.
           return jsonify({"error": "Unauthorized"}), 403

        events_ref = db.collection("events").where("organizerId", "==", uid)
        events = [doc.to_dict() for doc in events_ref.stream()]
        return jsonify(events), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- User Registration ---
@app.route("/events/<event_id>/register", methods=["POST"])
@verify_token
def register_event(event_id):
    try:
        user_id = request.uid
        # Basic validation to avoid double registrations.
        registration_ref = db.collection('registrations').where('user_id', '==', user_id).where('event_id', '==', event_id).limit(1)
        if any(registration_ref.stream()):
            return jsonify({"error": "Already registered"}), 409 # Conflict Error

        db.collection("registrations").add({"user_id": user_id, "event_id": event_id})
        return jsonify({"message": "User registered for event"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/registrations/<user_id>", methods=["GET"])
@verify_token
def get_user_registrations(user_id):
    try:
        if request.uid != user_id:
            return jsonify({"error": "Unauthorized"}), 403
        registrations = []
        registration_docs = db.collection("registrations").where("user_id", "==", user_id).stream()
        for doc in registration_docs:
            registration_data = doc.to_dict()
            event_id = registration_data.get("event_id")
            if event_id:
                event_doc = db.collection("events").document(event_id).get()
                if event_doc.exists:
                    event_data = event_doc.to_dict()
                    registrations.append(event_data)
        return jsonify(registrations), 200
    except Exception as e:
        print(e) #log the error
        return jsonify({"error": str(e)}), 500
from functools import wraps

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
