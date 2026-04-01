from flask import Flask, request, jsonify
import random
import time
import requests   # ✅ NEW

app = Flask(__name__)

# ---------------- CONFIG ----------------
FAST2SMS_API_KEY = "ZWSf5uQHn1XsiFlx7B4Yw9UDkvKzCeROjM02otNVTdypqcAbLEOka8MPD1TNUVv6Sdo0nClwgb42ExQK"   # 🔥 PUT YOUR REAL API KEY

OTP_EXPIRY = 120   # seconds (2 minutes)

otp_store = {}     # {mobile: {"otp": "1234", "time": 123456}}
sessions = {}      # {mobile: "active"}
users = {}         # {mobile: {"name": "", "email": ""}}

# ---------------- SEND SMS FUNCTION ----------------
def send_sms(mobile, otp):
    try:
        url = "https://www.fast2sms.com/dev/bulkV2"

        payload = {
            "sender_id": "FSTSMS",
            "message": f"Your OTP is {otp}",
            "language": "english",
            "route": "q",
            "numbers": mobile
        }

        headers = {
            "authorization": FAST2SMS_API_KEY,
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        print("SMS API Response:", response.text)

    except Exception as e:
        print("SMS Error:", str(e))


# ---------------- SEND OTP ----------------
@app.route("/send_otp", methods=["POST"])
def send_otp():
    data = request.json
    mobile = data.get("mobile")

    if not mobile or len(mobile) < 10:
        return jsonify({"status": "error", "message": "Invalid mobile number"})

    # ✅ Ensure country code (India)
    if not mobile.startswith("91"):
        mobile = "91" + mobile

    otp = str(random.randint(1000, 9999))

    otp_store[mobile] = {
        "otp": otp,
        "time": time.time()
    }

    # 🔥 SEND SMS HERE
    send_sms(mobile, otp)

    print(f"OTP sent to {mobile}: {otp}")  # backup log

    return jsonify({"status": "otp_sent"})


# ---------------- VERIFY OTP ----------------
@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    data = request.json

    mobile = data.get("mobile")
    otp = data.get("otp")
    name = data.get("name")
    email = data.get("email")

    # Ensure same format as stored
    if not mobile.startswith("91"):
        mobile = "91" + mobile

    record = otp_store.get(mobile)

    if not record:
        return jsonify({"status": "failed", "message": "No OTP found"})

    # Check expiry
    if time.time() - record["time"] > OTP_EXPIRY:
        return jsonify({"status": "expired"})

    if record["otp"] == otp:
        sessions[mobile] = "active"

        users[mobile] = {
            "name": name,
            "email": email
        }

        # Remove OTP after success
        otp_store.pop(mobile, None)

        return jsonify({"status": "verified"})
    else:
        return jsonify({"status": "invalid"})


# ---------------- CHECK SESSION ----------------
@app.route("/check_session", methods=["POST"])
def check_session():
    data = request.json
    mobile = data.get("mobile")

    if not mobile.startswith("91"):
        mobile = "91" + mobile

    if sessions.get(mobile) == "active":
        return jsonify({"status": "active"})
    else:
        return jsonify({"status": "inactive"})


# ---------------- LOGOUT ----------------
@app.route("/logout", methods=["POST"])
def logout():
    data = request.json
    mobile = data.get("mobile")

    if not mobile.startswith("91"):
        mobile = "91" + mobile

    sessions.pop(mobile, None)

    return jsonify({"status": "logged_out"})


# ---------------- HEALTH CHECK ----------------
@app.route("/", methods=["GET"])
def home():
    return "Server is running"


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
