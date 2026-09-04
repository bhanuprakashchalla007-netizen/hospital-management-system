from flask import Flask, render_template, request, jsonify, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import os
import re

# ============================================================
# OPTIONAL OPENAI IMPORT
# ============================================================

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# ============================================================
# FLASK CONFIGURATION
# ============================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "hospital-management-secret-key-change-this"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "hospital_data.json")

os.makedirs(DATA_DIR, exist_ok=True)


# ============================================================
# OPENAI CONFIGURATION
# ============================================================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if OPENAI_AVAILABLE and OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        client = None
else:
    client = None

OPENAI_MODEL = "gpt-5.6-luna"


# ============================================================
# DATA MANAGEMENT
# ============================================================

def empty_data():
    return {
        "patients": [],
        "doctors": [],
        "appointments": [],
        "bills": [],
        "users": []
    }


def load_data():
    if not os.path.exists(DATA_FILE):
        return empty_data()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        default = empty_data()

        for key in default:
            if key not in data:
                data[key] = []

        return data

    except Exception as e:
        print("Error loading data:", e)
        return empty_data()


def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

        return True

    except Exception as e:
        print("Error saving data:", e)
        return False


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def generate_id(prefix):
    timestamp = int(datetime.now().timestamp() * 1000)
    return f"{prefix}_{timestamp}"


def get_current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    data = load_data()

    for user in data.get("users", []):
        if user.get("id") == user_id:
            return user

    return None


def normalize_text(text):
    if not text:
        return ""

    return re.sub(r"\s+", " ", text.lower().strip())


# ============================================================
# STATISTICS
# ============================================================

def get_stats(data=None):
    """Return every statistic required by dashboard.html."""
    if data is None:
        data = load_data()

    patients = data.get("patients", []) or []
    doctors = data.get("doctors", []) or []
    appointments = data.get("appointments", []) or []
    bills = data.get("bills", []) or []

    def amount(bill):
        try:
            return float(bill.get("total_amount", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    total_revenue = sum(amount(b) for b in bills)
    paid_revenue = sum(amount(b) for b in bills if b.get("is_paid", False))
    pending_revenue = total_revenue - paid_revenue

    status_counts = {}
    for appointment in appointments:
        status = str(appointment.get("status", "Scheduled") or "Scheduled")
        status_counts[status] = status_counts.get(status, 0) + 1

    blood_dist = {}
    for patient in patients:
        group = patient.get("blood_group", "Unknown") or "Unknown"
        blood_dist[group] = blood_dist.get(group, 0) + 1

    disease_dist = {}
    for patient in patients:
        disease = patient.get("disease", "Unknown") or "Unknown"
        disease_dist[disease] = disease_dist.get(disease, 0) + 1
    disease_dist = dict(sorted(disease_dist.items(), key=lambda x: x[1], reverse=True)[:6])

    dept_dist = {}
    for doctor in doctors:
        dept = doctor.get("department", doctor.get("specialization", "Unknown")) or "Unknown"
        dept_dist[dept] = dept_dist.get(dept, 0) + 1

    doc_workload = {}
    for appointment in appointments:
        name = appointment.get("doctor_name", "Unknown") or "Unknown"
        doc_workload[name] = doc_workload.get(name, 0) + 1

    return {
        "total_patients": len(patients),
        "total_doctors": len(doctors),
        "total_appointments": len(appointments),
        "total_bills": len(bills),
        "total_revenue": round(total_revenue, 2),
        "paid_revenue": round(paid_revenue, 2),
        "pending_revenue": round(pending_revenue, 2),
        "appt_scheduled": status_counts.get("Scheduled", 0) + status_counts.get("Booked", 0) + status_counts.get("Pending", 0),
        "appt_completed": status_counts.get("Completed", 0) + status_counts.get("Confirmed", 0),
        "appt_cancelled": status_counts.get("Cancelled", 0) + status_counts.get("Rejected", 0),
        "blood_dist": blood_dist,
        "disease_dist": disease_dist,
        "dept_dist": dept_dist,
        "doc_workload": doc_workload,
        "paid_count": sum(1 for b in bills if b.get("is_paid", False)),
        "pending_count": sum(1 for b in bills if not b.get("is_paid", False))
    }


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


# ============================================================
# USER AUTHENTICATION
# ============================================================

@app.route("/user")
def user_auth():
    if session.get("user_id"):
        return redirect("/user/dashboard")

    return render_template("user_auth.html")


# ---------------- USER SIGNUP ----------------

@app.route("/api/user/signup", methods=["POST"])
def user_signup():

    try:
        data = request.get_json() or {}

        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        phone = data.get("phone", "").strip()
        dob = data.get("dob", "").strip()
        gender = data.get("gender", "").strip()
        blood_group = data.get("blood_group", "").strip()
        password = data.get("password", "")
        confirm_password = data.get("confirm_password", "")

        if not name:
            return jsonify({
                "success": False,
                "message": "Please enter your full name."
            })

        if not email:
            return jsonify({
                "success": False,
                "message": "Please enter your email."
            })

        if not phone:
            return jsonify({
                "success": False,
                "message": "Please enter your phone number."
            })

        if not dob:
            return jsonify({
                "success": False,
                "message": "Please enter your date of birth."
            })

        if not gender:
            return jsonify({
                "success": False,
                "message": "Please select your gender."
            })

        if not blood_group:
            return jsonify({
                "success": False,
                "message": "Please select your blood group."
            })

        if not password:
            return jsonify({
                "success": False,
                "message": "Please enter a password."
            })

        if len(password) < 6:
            return jsonify({
                "success": False,
                "message": "Password must contain at least 6 characters."
            })

        if password != confirm_password:
            return jsonify({
                "success": False,
                "message": "Passwords do not match."
            })

        data_store = load_data()

        for user in data_store.get("users", []):

            if user.get("email", "").lower() == email:
                return jsonify({
                    "success": False,
                    "message": "An account with this email already exists."
                })

        user = {
            "id": generate_id("USR"),
            "name": name,
            "email": email,
            "phone": phone,
            "dob": dob,
            "gender": gender,
            "blood_group": blood_group,
            "password": generate_password_hash(password),
            "created_at": datetime.now().isoformat()
        }

        data_store["users"].append(user)

        if not save_data(data_store):
            return jsonify({
                "success": False,
                "message": "Unable to create account. Please try again."
            })

        session["user_id"] = user["id"]

        return jsonify({
            "success": True,
            "message": "Account created successfully.",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"]
            }
        })

    except Exception as e:

        print("Signup error:", e)

        return jsonify({
            "success": False,
            "message": "Something went wrong while creating your account."
        }), 500


# ---------------- USER LOGIN ----------------

@app.route("/api/user/login", methods=["POST"])
def user_login():

    try:
        data = request.get_json() or {}

        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            return jsonify({
                "success": False,
                "message": "Please enter email and password."
            })

        data_store = load_data()

        for user in data_store.get("users", []):

            if user.get("email", "").lower() == email:

                if check_password_hash(
                    user.get("password", ""),
                    password
                ):

                    session["user_id"] = user.get("id")

                    return jsonify({
                        "success": True,
                        "message": "Login successful.",
                        "user": {
                            "id": user.get("id"),
                            "name": user.get("name"),
                            "email": user.get("email")
                        }
                    })

                return jsonify({
                    "success": False,
                    "message": "Incorrect password."
                })

        return jsonify({
            "success": False,
            "message": "No account found with this email."
        })

    except Exception as e:

        print("Login error:", e)

        return jsonify({
            "success": False,
            "message": "Unable to login right now."
        }), 500


# ============================================================
# USER DASHBOARD
# ============================================================

@app.route("/user/dashboard")
def user_dashboard():

    user = get_current_user()

    if not user:
        return redirect("/user")

    data = load_data()

    user_id = user.get("id")

    user_appointments = []

    for appointment in data.get("appointments", []):

        if appointment.get("user_id") == user_id:
            user_appointments.append(appointment)

    # Find doctors previously consulted
    consulted_doctors = []

    doctor_ids = set()

    for appointment in user_appointments:

        doctor_id = appointment.get("doctor_id")

        if doctor_id:
            doctor_ids.add(str(doctor_id))

    for doctor in data.get("doctors", []):

        if str(doctor.get("id")) in doctor_ids:
            consulted_doctors.append(doctor)

    return render_template(
        "user_dashboard.html",
        user=user,
        appointments=user_appointments,
        doctors=consulted_doctors
    )


# ============================================================
# USER LOGOUT
# ============================================================

@app.route("/user/logout")
def user_logout():

    session.pop("user_id", None)

    return redirect("/")


# ============================================================
# MANAGEMENT DASHBOARD
# ============================================================

@app.route("/dashboard")
def management_dashboard():
    data = load_data()
    stats = get_stats(data)

    return render_template(
        "dashboard.html",
        data=data,
        stats=stats,
        hospital=data.get("hospital", "Hospital"),
        last_updated=datetime.now().strftime("%d %b %Y, %I:%M %p")
    )


# ============================================================
# AI PAGE
# ============================================================

@app.route("/ai")
def ai_page():
    return render_template("ai.html")


# ============================================================
# API - COMPLETE DATA
# ============================================================

@app.route("/api/data")
def api_data():

    data = load_data()

    return jsonify(data)


# ============================================================
# API - STATISTICS
# ============================================================

@app.route("/api/stats")
def api_stats():

    return jsonify({
        "success": True,
        "stats": get_stats()
    })


# ============================================================
# AI MEDICAL GUIDANCE
# ============================================================

MEDICAL_KEYWORDS = {

    "headache": {
        "specialization": "General Physician",
        "keywords": [
            "headache",
            "head pain",
            "migraine",
            "head ache"
        ]
    },

    "cold": {
        "specialization": "General Physician",
        "keywords": [
            "cold",
            "runny nose",
            "blocked nose",
            "stuffy nose",
            "sneezing"
        ]
    },

    "cough": {
        "specialization": "General Physician",
        "keywords": [
            "cough",
            "sore throat",
            "throat pain",
            "phlegm"
        ]
    },

    "fever": {
        "specialization": "General Physician",
        "keywords": [
            "fever",
            "temperature",
            "chills"
        ]
    },

    "stomach": {
        "specialization": "Gastroenterologist",
        "keywords": [
            "stomach pain",
            "stomach ache",
            "abdominal pain",
            "gas",
            "acidity",
            "indigestion",
            "bloating"
        ]
    },

    "skin": {
        "specialization": "Dermatologist",
        "keywords": [
            "rash",
            "itching",
            "skin problem",
            "acne",
            "pimples",
            "skin infection"
        ]
    },

    "bone": {
        "specialization": "Orthopedic",
        "keywords": [
            "back pain",
            "knee pain",
            "joint pain",
            "bone pain",
            "shoulder pain",
            "neck pain"
        ]
    },

    "heart": {
        "specialization": "Cardiologist",
        "keywords": [
            "chest pain",
            "heart pain",
            "palpitations",
            "fast heartbeat"
        ]
    },

    "eye": {
        "specialization": "Ophthalmologist",
        "keywords": [
            "eye pain",
            "red eyes",
            "blurred vision",
            "eye problem"
        ]
    },

    "ear": {
        "specialization": "ENT Specialist",
        "keywords": [
            "ear pain",
            "ear problem",
            "hearing problem",
            "sinus",
            "tonsil"
        ]
    }
}


def detect_specialization(message):

    text = normalize_text(message)

    matched_category = None
    matched_specialization = None

    for category, info in MEDICAL_KEYWORDS.items():

        for keyword in info["keywords"]:

            if keyword in text:

                matched_category = category
                matched_specialization = info["specialization"]
                break

        if matched_category:
            break

    return matched_category, matched_specialization


# ============================================================
# AI FALLBACK GUIDANCE
# ============================================================

def fallback_medical_guidance(message):

    text = normalize_text(message)

    category, specialization = detect_specialization(text)

    if category == "headache":

        return {
            "message": """
### Possible common causes
A mild headache can sometimes be associated with dehydration,
lack of sleep, stress, screen exposure, skipped meals, or a
common migraine-type headache.

### What you can try
• Drink enough water.
• Rest in a quiet environment.
• Take a break from screens.
• Eat a regular meal if you have skipped one.
• Try to maintain a regular sleep schedule.

### Watch for warning signs
Seek urgent medical attention if the headache is sudden and
extremely severe, follows a significant head injury, or occurs
with confusion, fainting, weakness, difficulty speaking,
seizures, or serious vision changes.

If headaches keep returning or do not improve, consider seeing
a General Physician.
""",
            "specialization": specialization,
            "category": category
        }

    if category == "cold":

        return {
            "message": """
### Possible common causes
A runny or blocked nose and sneezing are commonly associated
with a viral cold or allergies.

### What you can try
• Drink plenty of fluids.
• Rest adequately.
• Use warm fluids if they feel soothing.
• Avoid known allergy triggers when possible.
• Keep your surroundings clean.

### Watch for warning signs
Seek medical attention if you develop difficulty breathing,
persistent high fever, severe weakness, dehydration, or symptoms
that are becoming significantly worse.

A General Physician can evaluate persistent symptoms.
""",
            "specialization": specialization,
            "category": category
        }

    if category == "cough":

        return {
            "message": """
### Possible common causes
A cough or sore throat can occur with a common viral infection,
allergies, throat irritation, or other respiratory conditions.

### What you can try
• Stay hydrated.
• Rest your voice.
• Warm fluids may soothe an irritated throat.
• Avoid smoke and other respiratory irritants.

### Watch for warning signs
Get medical help promptly if you have significant breathing
difficulty, chest pain, coughing up blood, severe weakness,
or rapidly worsening symptoms.

A General Physician can assess a persistent cough.
""",
            "specialization": specialization,
            "category": category
        }

    if category == "fever":

        return {
            "message": """
### Possible common causes
Fever can occur with many infections and other conditions.
The cause cannot be determined from fever alone.

### What you can try
• Drink plenty of fluids.
• Rest.
• Monitor your temperature.
• Wear comfortable clothing and avoid overheating.

### Watch for warning signs
Seek medical attention if the fever is severe or persistent,
or if it occurs with confusion, difficulty breathing, severe
weakness, dehydration, seizures, or other serious symptoms.

A General Physician is a suitable first point of evaluation.
""",
            "specialization": specialization,
            "category": category
        }

    if category == "stomach":

        return {
            "message": """
### Possible common causes
Mild stomach discomfort can sometimes be related to indigestion,
gas, acidity, dietary changes, or a minor stomach infection.

### What you can try
• Drink water regularly.
• Eat lighter meals if heavy food makes symptoms worse.
• Avoid foods that you know trigger your symptoms.
• Rest and monitor how the symptoms change.

### Watch for warning signs
Seek medical attention for severe or worsening abdominal pain,
persistent vomiting, blood in vomit or stool, fainting, or
significant dehydration.

For recurring or persistent digestive symptoms, consider a
Gastroenterologist or General Physician.
""",
            "specialization": specialization,
            "category": category
        }

    if category == "skin":

        return {
            "message": """
### Possible common causes
Rashes, itching, or acne can have many causes including
irritation, allergies, acne, or skin infections.

### What you can try
• Keep the affected area clean.
• Avoid scratching.
• Avoid using multiple new cosmetic or skin products at once.
• Stop using a product if it clearly irritates your skin.

### Watch for warning signs
Seek medical attention if there is rapidly spreading redness,
severe swelling, breathing difficulty, facial swelling, high
fever, or a rapidly worsening skin reaction.

A Dermatologist can evaluate persistent skin problems.
""",
            "specialization": specialization,
            "category": category
        }

    if category == "bone":

        return {
            "message": """
### Possible common causes
Mild muscle or joint pain can sometimes follow overuse,
poor posture, exercise, or minor strain.

### What you can try
• Rest the affected area.
• Avoid activities that clearly increase the pain.
• Maintain comfortable posture.
• Gentle movement may help if it does not worsen symptoms.

### Watch for warning signs
Seek medical attention for severe pain after an injury,
loss of movement, significant swelling, numbness, weakness,
or rapidly worsening symptoms.

An Orthopedic specialist can evaluate persistent joint or
musculoskeletal problems.
""",
            "specialization": specialization,
            "category": category
        }

    if category == "heart":

        return {
            "message": """
### Important
Chest pain or unusual heart-related symptoms should not be
self-diagnosed by an AI assistant.

If you currently have severe or persistent chest pain,
difficulty breathing, fainting, severe sweating, or pain
spreading to the arm, jaw, back, or shoulder, seek emergency
medical care immediately.

For non-emergency recurring symptoms, a Cardiologist or
General Physician can provide appropriate evaluation.
""",
            "specialization": specialization,
            "category": category
        }

    if category == "eye":

        return {
            "message": """
### Possible causes
Eye discomfort or redness can have many causes, including
irritation, dryness, allergies, or infection.

### What you can try
• Give your eyes regular screen breaks.
• Avoid rubbing your eyes.
• Keep your hands clean.
• Avoid sharing eye cosmetics or towels.

### Watch for warning signs
Seek urgent medical attention for sudden vision loss,
severe eye pain, major eye injury, or significant swelling.

An Ophthalmologist can evaluate persistent eye symptoms.
""",
            "specialization": specialization,
            "category": category
        }

    if category == "ear":

        return {
            "message": """
### Possible causes
Ear discomfort may be related to infections, congestion,
wax buildup, or other conditions.

### What you can try
• Avoid putting objects inside the ear.
• Keep the ear dry if it is irritated.
• Monitor whether symptoms are improving.

### Watch for warning signs
Seek medical attention for severe ear pain, sudden hearing
loss, significant dizziness, discharge, or symptoms after
a serious injury.

An ENT Specialist can evaluate persistent ear-related symptoms.
""",
            "specialization": specialization,
            "category": category
        }

    return {
        "message": """
I can help you understand common symptoms and guide you toward
the appropriate type of medical care.

Please describe:
• What symptoms you have
• How long you have had them
• How severe they are
• Your age
• Anything that makes them better or worse

For example:

"I have had a mild headache since this morning and I did not
sleep well last night."
""",
        "specialization": "General Physician",
        "category": "general"
    }


# ============================================================
# OPENAI MEDICAL GUIDANCE
# ============================================================

def ask_openai_medical_assistant(message):

    if not client:
        return fallback_medical_guidance(message)

    system_prompt = """
You are the AI Health Assistant inside a hospital management
application.

Your job is to provide safe, general health information for
common and potentially minor symptoms and help the user decide
what type of healthcare professional may be appropriate.

IMPORTANT SAFETY RULES:

1. Do not claim to be a doctor.
2. Do not give a definitive diagnosis.
3. Do not prescribe prescription medicines.
4. Do not tell the user to start, stop, or change prescription
   medication.
5. Do not provide dangerous treatment instructions.
6. Clearly distinguish possibilities from a diagnosis.
7. Ask useful follow-up questions when important information
   is missing.
8. Always consider urgent warning signs.
9. If emergency warning signs may be present, tell the user to
   seek urgent/emergency medical care rather than relying on AI.
10. Keep advice practical and understandable.
11. For common mild symptoms, provide reasonable general
    self-care guidance.
12. Recommend an appropriate medical specialization when useful.

Structure responses when appropriate:

### What it could be
Explain a few common possibilities without diagnosing.

### What you can do
Give safe general self-care steps.

### Watch for warning signs
Explain symptoms that should prompt urgent medical attention.

### Who to see
Suggest an appropriate healthcare professional.

If the user provides too little information, ask concise
follow-up questions.

Remember that this assistant provides general health information
and is not a replacement for an in-person medical evaluation.
"""

    try:

        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions=system_prompt,
            input=message
        )

        answer = response.output_text

        if not answer:
            return fallback_medical_guidance(message)

        category, specialization = detect_specialization(message)

        if not specialization:
            specialization = "General Physician"

        return {
            "message": answer,
            "specialization": specialization,
            "category": category or "general"
        }

    except Exception as e:

        print("OpenAI error:", e)

        return fallback_medical_guidance(message)


# ============================================================
# FIND DOCTORS BY SPECIALIZATION
# ============================================================

def find_doctors_by_specialization(specialization):

    data = load_data()

    doctors = []

    specialization_normalized = normalize_text(specialization)

    for doctor in data.get("doctors", []):

        doctor_specialization = normalize_text(
            doctor.get("specialization", "")
        )

        doctor_department = normalize_text(
            doctor.get("department", "")
        )

        if (
            specialization_normalized in doctor_specialization
            or doctor_specialization in specialization_normalized
            or specialization_normalized in doctor_department
            or doctor_department in specialization_normalized
        ):

            doctors.append(doctor)

    return doctors


# ============================================================
# AI API
# ============================================================

@app.route("/api/ai", methods=["POST"])
def ai_assistant():

    try:

        data = request.get_json() or {}

        message = data.get("message", "").strip()

        if not message:

            return jsonify({
                "success": False,
                "message": "Please describe your symptoms."
            })

        if len(message) > 5000:

            return jsonify({
                "success": False,
                "message": "Please keep your message under 5000 characters."
            })

        ai_result = ask_openai_medical_assistant(message)

        specialization = ai_result.get(
            "specialization",
            "General Physician"
        )

        doctors = find_doctors_by_specialization(
            specialization
        )

        return jsonify({
            "success": True,
            "message": ai_result.get("message", ""),
            "specialization": specialization,
            "category": ai_result.get("category", "general"),
            "doctors": doctors
        })

    except Exception as e:

        print("AI API error:", e)

        return jsonify({
            "success": False,
            "message": "The AI assistant is temporarily unavailable."
        }), 500


# ============================================================
# CHECK DOCTOR AVAILABILITY
# ============================================================

@app.route("/api/check-availability", methods=["POST"])
def check_availability():

    try:

        data = request.get_json() or {}

        doctor_id = str(data.get("doctor_id", "")).strip()
        date = data.get("date", "").strip()

        if not doctor_id or not date:

            return jsonify({
                "success": False,
                "message": "Doctor and date are required."
            })

        store = load_data()

        doctor = None

        for d in store.get("doctors", []):

            if str(d.get("id")) == doctor_id:
                doctor = d
                break

        if not doctor:

            return jsonify({
                "success": False,
                "message": "Doctor not found."
            })

        # Common available slots
        default_slots = [
            "09:00 AM",
            "10:00 AM",
            "11:00 AM",
            "12:00 PM",
            "02:00 PM",
            "03:00 PM",
            "04:00 PM",
            "05:00 PM"
        ]

        slots = doctor.get(
            "available_slots",
            default_slots
        )

        booked_slots = []

        for appointment in store.get("appointments", []):

            if (
                str(appointment.get("doctor_id")) == doctor_id
                and appointment.get("date") == date
                and appointment.get("status", "Booked") != "Cancelled"
            ):

                booked_slots.append(
                    appointment.get("time_slot")
                )

        available_slots = [
            slot for slot in slots
            if slot not in booked_slots
        ]

        return jsonify({
            "success": True,
            "doctor": doctor,
            "date": date,
            "slots": available_slots
        })

    except Exception as e:

        print("Availability error:", e)

        return jsonify({
            "success": False,
            "message": "Unable to check availability."
        }), 500
# ============================================================
# DOCTOR PORTAL ENTRY
# ============================================================

@app.route("/doctor")
def doctor_portal():
    if session.get("doctor_id"):
        return redirect("/doctor/dashboard")
    return redirect("/doctor/login")


# ============================================================
# DOCTOR AUTHENTICATION
# ============================================================

@app.route("/doctor/login", methods=["GET", "POST"])
def doctor_login():

    # Show login page
    if request.method == "GET":
        return render_template("doctor_login.html")

    try:

        data = request.get_json() or {}

        doctor_id = str(
            data.get("doctor_id", "")
        ).strip()

        password = data.get(
            "password",
            ""
        )

        if not doctor_id or not password:

            return jsonify({
                "success": False,
                "message": "Please enter Doctor ID and password."
            })

        store = load_data()

        doctor = None

        for d in store.get("doctors", []):

            # Allow login using ID or email
            if (
                str(d.get("id", "")).lower()
                == doctor_id.lower()
                or
                str(d.get("email", "")).lower()
                == doctor_id.lower()
            ):

                doctor = d
                break

        if not doctor:

            return jsonify({
                "success": False,
                "message": "Doctor account not found."
            })

        # ----------------------------------------------------
        # PASSWORD CHECK
        # ----------------------------------------------------

        stored_password = doctor.get(
            "password",
            ""
        )

        password_valid = False

        # Hashed password
        if stored_password:

            try:

                password_valid = check_password_hash(
                    stored_password,
                    password
                )

            except Exception:

                password_valid = (
                    stored_password == password
                )

        if not password_valid:

            return jsonify({
                "success": False,
                "message": "Incorrect password."
            })

        # ----------------------------------------------------
        # DOCTOR SESSION
        # ----------------------------------------------------

        session["doctor_id"] = doctor.get("id")

        return jsonify({

            "success": True,

            "message": "Doctor login successful.",

            "doctor": {
                "id": doctor.get("id"),
                "name": doctor.get(
                    "name",
                    "Doctor"
                ),
                "email": doctor.get(
                    "email",
                    ""
                ),
                "specialization": doctor.get(
                    "specialization",
                    ""
                )
            }

        })

    except Exception as e:

        print(
            "Doctor login error:",
            e
        )

        return jsonify({

            "success": False,

            "message":
                "Unable to login right now."

        }), 500


# ============================================================
# DOCTOR HELPER
# ============================================================

def get_current_doctor():

    doctor_id = session.get(
        "doctor_id"
    )

    if not doctor_id:
        return None

    store = load_data()

    for doctor in store.get(
        "doctors",
        []
    ):

        if str(
            doctor.get("id")
        ) == str(doctor_id):

            return doctor

    return None


# ============================================================
# DOCTOR DASHBOARD PAGE
# ============================================================

@app.route("/doctor/dashboard")
def doctor_dashboard():

    doctor = get_current_doctor()

    if not doctor:

        return redirect(
            "/doctor/login"
        )

    return render_template(
        "doctor_dashboard.html",
        doctor=doctor
    )


# ============================================================
# DOCTOR LOGOUT
# ============================================================

@app.route("/doctor/logout")
def doctor_logout():

    session.pop(
        "doctor_id",
        None
    )

    return redirect("/")


# ============================================================
# DOCTOR APPOINTMENTS
# ============================================================

@app.route("/api/doctor/appointments")
def doctor_appointments():

    doctor = get_current_doctor()

    if not doctor:

        return jsonify({

            "success": False,

            "message":
                "Doctor login required."

        }), 401

    store = load_data()

    doctor_id = str(
        doctor.get("id")
    )

    appointments = []

    for appointment in store.get(
        "appointments",
        []
    ):

        if str(
            appointment.get("doctor_id")
        ) == doctor_id:

            appointments.append(
                appointment
            )

    # Newest/current appointments first
    appointments.sort(
        key=lambda x: (
            x.get("date", ""),
            x.get("time_slot", "")
        )
    )

    return jsonify({

        "success": True,

        "doctor": {
            "id": doctor.get("id"),
            "name": doctor.get(
                "name",
                "Doctor"
            ),
            "specialization": doctor.get(
                "specialization",
                ""
            )
        },

        "appointments":
            appointments

    })


# ============================================================
# ACCEPT / REJECT APPOINTMENT
# ============================================================

@app.route(
    "/api/doctor/appointment-status",
    methods=["POST"]
)
def doctor_appointment_status():

    doctor = get_current_doctor()

    if not doctor:

        return jsonify({

            "success": False,

            "message":
                "Doctor login required."

        }), 401

    try:

        data = request.get_json() or {}

        appointment_id = str(
            data.get(
                "appointment_id",
                ""
            )
        ).strip()

        status = str(
            data.get(
                "status",
                ""
            )
        ).strip()

        allowed_statuses = [
            "Confirmed",
            "Rejected"
        ]

        if not appointment_id:

            return jsonify({

                "success": False,

                "message":
                    "Appointment ID is required."

            }), 400

        if status not in allowed_statuses:

            return jsonify({

                "success": False,

                "message":
                    "Invalid appointment status."

            }), 400

        store = load_data()

        doctor_id = str(
            doctor.get("id")
        )

        appointment = None

        for item in store.get(
            "appointments",
            []
        ):

            if (
                str(
                    item.get("id")
                ) == appointment_id
                and
                str(
                    item.get("doctor_id")
                ) == doctor_id
            ):

                appointment = item
                break

        if not appointment:

            return jsonify({

                "success": False,

                "message":
                    "Appointment not found."

            }), 404

        current_status = appointment.get(
            "status",
            "Booked"
        )

        if current_status in [
            "Completed",
            "Cancelled",
            "Rejected"
        ]:

            return jsonify({

                "success": False,

                "message":
                    "This appointment can no longer be changed."

            }), 400

        appointment["status"] = status

        appointment[
            "updated_at"
        ] = datetime.now().isoformat()

        if not save_data(store):

            return jsonify({

                "success": False,

                "message":
                    "Unable to save appointment status."

            }), 500

        return jsonify({

            "success": True,

            "message":
                f"Appointment {status.lower()} successfully.",

            "appointment":
                appointment

        })

    except Exception as e:

        print(
            "Appointment status error:",
            e
        )

        return jsonify({

            "success": False,

            "message":
                "Unable to update appointment."

        }), 500


# ============================================================
# DOCTOR PATIENT DETAILS
# ============================================================

@app.route(
    "/doctor/patient/<appointment_id>"
)
def doctor_patient(appointment_id):

    doctor = get_current_doctor()

    if not doctor:

        return redirect(
            "/doctor/login"
        )

    store = load_data()

    doctor_id = str(
        doctor.get("id")
    )

    appointment = None

    for item in store.get(
        "appointments",
        []
    ):

        if (
            str(item.get("id"))
            == str(appointment_id)
            and
            str(item.get("doctor_id"))
            == doctor_id
        ):

            appointment = item

            break

    if not appointment:

        return "Appointment not found.", 404

    patient_id = appointment.get(
        "patient_id"
    )

    patient = None

    # Search users first
    for user in store.get(
        "users",
        []
    ):

        if str(
            user.get("id")
        ) == str(patient_id):

            patient = user
            break

    # Search patients if not found
    if not patient:

        for item in store.get(
            "patients",
            []
        ):

            if str(
                item.get("id")
            ) == str(patient_id):

                patient = item
                break

    if not patient:

        patient = {

            "name":
                appointment.get(
                    "patient_name",
                    "Patient"
                ),

            "id":
                patient_id or "N/A"

        }

    # Patient's previous appointments
    history = []

    for item in store.get(
        "appointments",
        []
    ):

        if str(
            item.get("patient_id")
        ) == str(patient_id):

            history.append(item)

    history.sort(
        key=lambda x:
            x.get("date", ""),
        reverse=True
    )

    return render_template(
        "patient_details.html",
        doctor=doctor,
        patient=patient,
        appointment=appointment,
        history=history
    )



# ============================================================
# BOOK APPOINTMENT
# ============================================================

@app.route("/api/book-appointment", methods=["POST"])
def book_appointment():

    try:

        data = request.get_json() or {}

        patient_name = data.get("patient_name", "").strip()
        doctor_id = str(data.get("doctor_id", "")).strip()
        date = data.get("date", "").strip()
        time_slot = data.get("time_slot", "").strip()

        # Logged-in user
        current_user = get_current_user()

        # If user is logged in, use their real name
        if current_user:

            patient_name = current_user.get(
                "name",
                patient_name
            )

        if not patient_name:

            return jsonify({
                "success": False,
                "message": "Patient name is required."
            })

        if not doctor_id:

            return jsonify({
                "success": False,
                "message": "Doctor is required."
            })

        if not date:

            return jsonify({
                "success": False,
                "message": "Appointment date is required."
            })

        if not time_slot:

            return jsonify({
                "success": False,
                "message": "Please select a time slot."
            })

        store = load_data()

        doctor = None

        for d in store.get("doctors", []):

            if str(d.get("id")) == doctor_id:
                doctor = d
                break

        if not doctor:

            return jsonify({
                "success": False,
                "message": "Doctor not found."
            })

        # Prevent duplicate booking
        for appointment in store.get("appointments", []):

            same_doctor = (
                str(appointment.get("doctor_id"))
                == doctor_id
            )

            same_date = (
                appointment.get("date")
                == date
            )

            same_slot = (
                appointment.get("time_slot")
                == time_slot
            )

            active = (
                appointment.get("status", "Booked")
                != "Cancelled"
            )

            if (
                same_doctor
                and same_date
                and same_slot
                and active
            ):

                return jsonify({
                    "success": False,
                    "message": "This time slot has already been booked."
                })

        appointment = {
            "id": generate_id("APT"),

            # Important for User Dashboard
            "user_id": (
                current_user.get("id")
                if current_user
                else None
            ),

            "patient_name": patient_name,

            "patient_id": (
                current_user.get("id")
                if current_user
                else None
            ),

            "doctor_id": doctor_id,

            "doctor_name": doctor.get(
                "name",
                "Doctor"
            ),

            "specialization": doctor.get(
                "specialization",
                ""
            ),

            "date": date,

            "time_slot": time_slot,

            "status": "Booked",

            "created_at": datetime.now().isoformat()
        }

        store.setdefault(
            "appointments",
            []
        ).append(appointment)

        if not save_data(store):

            return jsonify({
                "success": False,
                "message": "Unable to save appointment."
            })

        return jsonify({
            "success": True,
            "message": "Appointment booked successfully.",
            "appointment": appointment
        })

    except Exception as e:

        print("Booking error:", e)

        return jsonify({
            "success": False,
            "message": "Unable to book appointment."
        }), 500


# ============================================================
# USER APPOINTMENTS
# ============================================================

@app.route("/api/user/appointments")
def user_appointments():

    user = get_current_user()

    if not user:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    data = load_data()

    user_id = user.get("id")

    appointments = [
        appointment
        for appointment in data.get("appointments", [])
        if appointment.get("user_id") == user_id
    ]

    return jsonify({
        "success": True,
        "appointments": appointments
    })


# ============================================================
# USER CONSULTED DOCTORS
# ============================================================

@app.route("/api/user/doctors")
def user_doctors():

    user = get_current_user()

    if not user:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    data = load_data()

    user_id = user.get("id")

    doctor_ids = set()

    for appointment in data.get("appointments", []):

        if appointment.get("user_id") == user_id:

            doctor_id = appointment.get("doctor_id")

            if doctor_id:
                doctor_ids.add(str(doctor_id))

    doctors = []

    for doctor in data.get("doctors", []):

        if str(doctor.get("id")) in doctor_ids:
            doctors.append(doctor)

    return jsonify({
        "success": True,
        "doctors": doctors
    })


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("🏥 HOSPITAL MANAGEMENT SYSTEM")
    print("=" * 60)

    print("Server starting...")

    if client:
        print("🤖 OpenAI AI Assistant: ENABLED")
    else:
        print("🤖 OpenAI AI Assistant: FALLBACK MODE")

    print("🌐 http://127.0.0.1:5000")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )