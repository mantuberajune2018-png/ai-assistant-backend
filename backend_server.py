from flask import Flask, request, jsonify
import random
import time
import os
import resend
from openai import OpenAI

app = Flask(__name__)

# ---------------- CONFIG ----------------
# Load your Resend API key from Render Environment Variables
resend.api_key = os.getenv("RESEND_API_KEY")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Resend allows you to use this default testing email to send messages
# to the email address you signed up with.
FROM_EMAIL = "no-reply@xgboostaitechnology.com"

OTP_EXPIRY = 180  # seconds (3 minutes)

otp_store = {}  # {email: {"otp": "1234", "time": 123456}}
sessions = {}  # {email: "active"}
users = {}  # {email: {"name": "", "mobile": ""}}


# ---------------- SEND EMAIL USING RESEND API ----------------
def send_email_otp(receiver_email, otp):
    try:
        params = {
            "from": FROM_EMAIL,
            "to": receiver_email,
            "subject": "Your AI Assistant OTP Code",
            "html": f"<p>Hello,</p><p>Your OTP is: <strong>{otp}</strong></p><p>This OTP is valid for 3 minutes.</p><p>- AI Assistant</p>"
        }

        # Send the email via API
        response = resend.Emails.send(params)
        print(f"SUCCESS: Email accepted by Resend API for {receiver_email}. Resend ID: {response}")
        return True

    except Exception as e:
        print(f"CRITICAL API EMAIL ERROR: {str(e)}")
        return False


# ---------------- SEND OTP ROUTE ----------------
@app.route("/send_otp", methods=["POST"])
def send_otp():
    data = request.json
    email = data.get("email")

    if not email or "@" not in email:
        return jsonify({"status": "error", "message": "Invalid email"})

    otp = str(random.randint(1000, 9999))

    # Attempt to send the email FIRST
    email_sent_successfully = send_email_otp(email, otp)

    if email_sent_successfully:
        # Only save the OTP if the email actually went through
        otp_store[email] = {
            "otp": otp,
            "time": time.time()
        }
        print(f"OTP formally sent and saved for {email}: {otp}")
        return jsonify({"status": "otp_sent"})
    else:
        # Tell the frontend the email failed
        return jsonify({"status": "error", "message": "Email API Error. Check Render Logs."}), 500


# ---------------- VERIFY OTP ----------------
@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    data = request.json

    email = data.get("email")
    otp = data.get("otp")
    name = data.get("name")
    mobile = data.get("mobile")

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
        users[email] = {"name": name, "mobile": mobile}
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
    return "Server is running via Resend API"

# --------------Block of New Brain--------------
@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    # Handle CORS preflight request if you decide to add CORS later
    if request.method == "OPTIONS":
        return jsonify({}), 200
        
    data = request.get_json()
    question = data.get("question")

    if not question:
        return jsonify({"status": "error", "message": "No question provided"}), 400

    try:
        # Securely call OpenAI from the backend
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using the current standard fast/cheap model
            messages=[{"role": "user", "content": question}]
        )
        answer = response.choices[0].message.content.strip()
        
        # Send the answer back to the frontend
        return jsonify({"status": "success", "answer": answer})
        
    except Exception as e:
        print("OpenAI Error:", e)
        return jsonify({"status": "error", "message": "Failed to get AI response"}), 500

# ---------------- RUN ----------------
if __name__ == '__main__':
    # Get the port from Render's environment, or use 5000 for local testing
    port = int(os.environ.get("PORT", 5000))
    # host="0.0.0.0" is required for Render to detect the open port
    app.run(host="0.0.0.0", port=port)
