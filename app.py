from flask import Flask, render_template, request, redirect
import firebase_admin
from firebase_admin import credentials, firestore
import json
import datetime
import threading
import time
from rfid_reader import read_rfid

# --------------------------
# FIREBASE INITIALIZATION
# --------------------------
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)

CACHE_FILE = "cache.json"


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
# RFID LISTENER (RUNS IN BACKGROUND)
# --------------------------
current_card = {"uid": None}
last_seen = 0


def rfid_listener():
    global current_card, last_seen

    while True:
        uid = read_rfid()

        if uid:
            current_card["uid"] = uid
            last_seen = time.time()
        else:
            # Auto-clear card after 3 seconds of no detection
            if time.time() - last_seen > 3:
                current_card["uid"] = None

        time.sleep(0.2)  # Faster, but non-blocking


threading.Thread(target=rfid_listener, daemon=True).start()


# --------------------------
# HOME ROUTE
# --------------------------
@app.route("/")
def home():
    if current_card["uid"] is None:
        return "<h2>Waiting for RFID card...</h2>"

    uid = current_card["uid"]
    doc_ref = db.collection("children").document(uid)
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        # Update last_scan
        doc_ref.update({"last_scan": datetime.datetime.utcnow().isoformat()})
        return render_template("dashboard.html", child=data)
    else:
        return render_template("new_registration.html", card_id=uid)


# --------------------------
# SAVE NEW REGISTRATION
# --------------------------
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

    # Vaccines (preset)
    vaccines = {
        "BCG": "null",
        "DTP1": "null",
        "DTP2": "null",
        "DTP3": "null",
        "Hepatitis_B1": "null",
        "Hepatitis_B2": "null",
        "Hepatitis_B3": "null",
        "IPV1": "null",
        "IPV2": "null",
        "IPV3": "null",
        "MMR1": "null",
        "OPV0": "null",
        "TD": "null"
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

    db.collection("children").document(card_id).set(data)

    # Cache last details locally
    save_cache(data)

    return redirect("/")


# --------------------------
# UPDATE EXISTING VACCINES
# --------------------------
@app.route("/update_vaccines", methods=["POST"])
def update_vaccines():
    card_id = request.form["card_id"]

    updated_vaccines = {}
    for key in request.form:
        if key.startswith("vaccine_"):
            vname = key.replace("vaccine_", "")
            updated_vaccines[vname] = request.form[key]

    db.collection("children").document(card_id).update({
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
