from flask import Flask, render_template, request, redirect, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import json
import datetime
import threading
import time
from rfid_reader import read_rfid  # your non-blocking RFID reader

# --------------------------
# FIREBASE INITIALIZATION
# --------------------------
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)

CACHE_FILE = "cache.json"

# --------------------------
# CACHE UTILITIES
# --------------------------
def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

def load_cache():
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

# --------------------------
# RFID LISTENER (BACKGROUND THREAD)
# --------------------------
current_card = {"uid": None}
last_seen = 0

def rfid_listener():
    global current_card, last_seen
    while True:
        uid = read_rfid()
        if uid:
            current_card["uid"] = str(uid)  # ensure it's a string
            last_seen = time.time()
        else:
            # Auto-clear card after 3 seconds of no detection
            if time.time() - last_seen > 3:
                current_card["uid"] = None
        time.sleep(0.2)

threading.Thread(target=rfid_listener, daemon=True).start()

# --------------------------
# ROUTES
# --------------------------
@app.route("/")
def home():
    return render_template("home.html")  # polling handled by JS

@app.route("/check_uid")
def check_uid():
    """AJAX endpoint to check if a card is present."""
    uid = current_card["uid"]
    return jsonify({"uid": uid})

@app.route("/card/<uid>")
def card_page(uid):
    """Show dashboard or new registration page based on card UID."""
    global current_card
    card_id = str(uid)
    doc_ref = db.collection("children").document("PANC123")
    doc = doc_ref.get()

    # Clear the UID after handling
    current_card["uid"] = None

    if doc.exists:
        data = doc.to_dict()
        if data.get('card_id'):
            doc_ref.update({"last_scan": datetime.datetime.utcnow().isoformat()})
            return render_template("dashboard.html", child=data)
        else:
            return render_template("new_registration.html", card_id=uid)

@app.route("/save_new", methods=["POST"])
def save_new():
    card_id = request.form["card_id"]
    name = request.form["name"]
    dob = request.form["dob"]
    parent_email = request.form["parent_email"]
    parent_phone = request.form["parent_phone"]
    state = request.form["state"]
    district = request.form["district"]
    panchayat = request.form["panchayat"]

    vaccines = {
        "BCG": "null", "DTP1": "null", "DTP2": "null", "DTP3": "null",
        "Hepatitis_B1": "null", "Hepatitis_B2": "null", "Hepatitis_B3": "null",
        "IPV1": "null", "IPV2": "null", "IPV3": "null",
        "MMR1": "null", "OPV0": "null", "TD": "null"
    }

    data = {
        "card_id": card_id,
        "clinic_id": card_id,
        "name": name,
        "dob": dob,
        "nfc_id": card_id,
        "parent_email": parent_email,
        "parent_phone": parent_phone,
        "region": {
            "state": state,
            "district": district,
            "panchayat": panchayat
        },
        "vaccines": vaccines,
        "status": "pending",
        "last_scan": datetime.datetime.utcnow().isoformat()
    }

    db.collection("children").document("PANC123").set(data)
    save_cache(data)
    return redirect("/")

@app.route("/update_vaccines", methods=["POST"])
def update_vaccines():
    card_id = request.form["card_id"]
    updated_vaccines = {k.replace("vaccine_", ""): v for k, v in request.form.items() if k.startswith("vaccine_")}

    db.collection("children").document("PANC123").update({
        "vaccines": updated_vaccines,
        "last_scan": datetime.datetime.utcnow().isoformat(),
        "status": "updated"
    })

    return redirect("/")

# --------------------------
# RUN APP
# --------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
