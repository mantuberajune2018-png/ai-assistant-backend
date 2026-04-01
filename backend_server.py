from flask import Flask, request, jsonify
import random
import time
import smtplib
import os
from email.mime.text import MIMEText

app = Flask(__name__)

# ---------------- CONFIG ----------------
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

OTP_EXPIRY = 180  # seconds (3 minutes)

otp_store = {}   # {email: {"otp": "1234", "time": 123456}}
sessions = {}    # {email: "active"}
users = {}       # {email: {"name": "", "mobile": ""}}

# ---------------- SEND EMAIL ----------------
def send_email_otp(receiver_email, otp):
    try:
        subject = "Your OTP Code"
        body = f"""
Hello,

Your OTP is: {otp}

This OTP is valid for 3 minutes.

Do not share this with anyone.

- AI Assistant
"""

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = receiver_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        print("Email sent to:", receiver_email)

    except Exception as e:
        print("Email Error:", str(e))


# ---------------- SEND OTP ----------------
@app.route("/send_otp", methods=["POST"])
def send_otp():
    data = request.json
    email = data.get("email")

    if not email or "@" not in email:
        return jsonify({"status": "error", "message": "Invalid email"})

    otp = str(random.randint(1000, 9999))

    otp_store[email] = {
        "otp": otp,
        "time": time.time()
    }

    send_email_otp(email, otp)

    print(f"OTP sent to {email}: {otp}")

    return jsonify({"status": "otp_sent"})


# ---------------- VERIFY OTP ----------------
@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    data = request.json

    email = data.get("email")
    otp = data.get("otp")
    name = data.get("name")
    mobile = data.get("mobile")  # just stored, not verified

    if not email:
        return jsonify({"status": "error", "message": "Email required"})

    record = otp_store.get(email)

    if not record:
        return jsonify({"status": "failed", "message": "No OTP found"})

    # Check expiry
    if time.time() - record["time"] > OTP_EXPIRY:
        otp_store.pop(email, None)
        return jsonify({"status": "expired"})

    if record["otp"] == otp:
        sessions[email] = "active"

        users[email] = {
            "name": name,
            "mobile": mobile
        }

        otp_store.pop(email, None)

        return jsonify({"status": "verified"})
    else:
        return jsonify({"status": "invalid"})


# ---------------- CHECK SESSION ----------------
@app.route("/check_session", methods=["POST"])
def check_session():
    email = request.json.get("email")

    if sessions.get(email) == "active":
        return jsonify({"status": "active"})
    else:
        return jsonify({"status": "inactive"})


# ---------------- LOGOUT ----------------
@app.route("/logout", methods=["POST"])
def logout():
    email = request.json.get("email")

    sessions.pop(email, None)

    return jsonify({"status": "logged_out"})


# ---------------- HEALTH CHECK ----------------
@app.route("/", methods=["GET"])
def home():
    return "Server is running"


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
