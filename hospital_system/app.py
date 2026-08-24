"""
Flask Dashboard — Hospital Management System
Reads data/hospital_data.json (written by C++ app)
Shows reports and summary statistics
"""

from flask import Flask, render_template, jsonify
import json
import os
from collections import Counter
from datetime import datetime

app = Flask(__name__)
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "hospital_data.json")

def load_data():
    """Read the JSON file written by the C++ application."""
    if not os.path.exists(DATA_FILE):
        return {"hospital": "City General Hospital",
                "patients": [], "doctors": [], "appointments": [], "bills": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def get_stats(data):
    patients     = data.get("patients", [])
    doctors      = data.get("doctors", [])
    appointments = data.get("appointments", [])
    bills        = data.get("bills", [])

    total_revenue   = sum(b["total_amount"] for b in bills)
    paid_revenue    = sum(b["total_amount"] for b in bills if b["is_paid"])
    pending_revenue = total_revenue - paid_revenue

    appt_status = Counter(a["status"] for a in appointments)
    blood_dist  = Counter(p["blood_group"] for p in patients)
    disease_dist = Counter(p["disease"] for p in patients)
    dept_dist   = Counter(d["department"] for d in doctors)

    # Doctor workload
    doc_workload = {}
    for a in appointments:
        dn = a["doctor_name"]
        doc_workload[dn] = doc_workload.get(dn, 0) + 1

    return {
        "total_patients":     len(patients),
        "total_doctors":      len(doctors),
        "total_appointments": len(appointments),
        "total_bills":        len(bills),
        "total_revenue":      round(total_revenue, 2),
        "paid_revenue":       round(paid_revenue, 2),
        "pending_revenue":    round(pending_revenue, 2),
        "appt_scheduled":     appt_status.get("Scheduled", 0),
        "appt_completed":     appt_status.get("Completed", 0),
        "appt_cancelled":     appt_status.get("Cancelled", 0),
        "blood_dist":         dict(blood_dist),
        "disease_dist":       dict(disease_dist.most_common(6)),
        "dept_dist":          dict(dept_dist),
        "doc_workload":       doc_workload,
        "paid_count":         sum(1 for b in bills if b["is_paid"]),
        "pending_count":      sum(1 for b in bills if not b["is_paid"]),
    }

@app.route("/")
def dashboard():
    data  = load_data()
    stats = get_stats(data)
    return render_template("dashboard.html",
                           data=data, stats=stats,
                           hospital=data.get("hospital", "Hospital"),
                           last_updated=datetime.now().strftime("%d %b %Y, %I:%M %p"))

@app.route("/api/data")
def api_data():
    return jsonify(load_data())

@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats(load_data()))

if __name__ == "__main__":
    print("=" * 50)
    print("  Flask Dashboard — Hospital Management System")
    print(f"  Reading data from: {DATA_FILE}")
    print("  Open: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
