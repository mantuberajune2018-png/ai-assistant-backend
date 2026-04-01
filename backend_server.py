from flask import Flask, request, jsonify
import random
import time

app = Flask(__name__)

otp_store = {}     # {mobile: {"otp": "1234", "time": 123456}}
sessions = {}      # {mobile: "active"}
users = {}         # {mobile: {"name": "", "email": ""}}

OTP_EXPIRY = 120   # seconds (2 minutes)

# ---------------- SEND OTP ----------------
@app.route("/send_otp", methods=["POST"])
def send_otp():
    data = request.json
    mobile = data.get("mobile")

    if not mobile or len(mobile) < 10:
        return jsonify({"status": "error", "message": "Invalid mobile number"})

    otp = str(random.randint(1000, 9999))

    otp_store[mobile] = {
        "otp": otp,
        "time": time.time()
    }

    print(f"OTP for {mobile}: {otp}")  # Replace with SMS API later

    return jsonify({"status": "otp_sent"})


# ---------------- VERIFY OTP ----------------
@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    data = request.json

    mobile = data.get("mobile")
    otp = data.get("otp")
    name = data.get("name")
    email = data.get("email")

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

    if sessions.get(mobile) == "active":
        return jsonify({"status": "active"})
    else:
        return jsonify({"status": "inactive"})


# ---------------- LOGOUT ----------------
@app.route("/logout", methods=["POST"])
def logout():
    data = request.json
    mobile = data.get("mobile")

    sessions.pop(mobile, None)

    return jsonify({"status": "logged_out"})


# ---------------- HEALTH CHECK ----------------
@app.route("/", methods=["GET"])
def home():
    return "Server is running"


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)