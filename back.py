from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import datetime

app = Flask(__name__)
CORS(app)

MEDICINES_FILE = "medicines.json"
HEALTH_FILE = "health.json"

def load_medicines():
    if os.path.exists(MEDICINES_FILE):
        with open(MEDICINES_FILE, "r") as f:
            return json.load(f)
    return []

def save_medicines(medicines):
    with open(MEDICINES_FILE, "w") as f:
        json.dump(medicines, f, indent=2)

def load_health():
    if os.path.exists(HEALTH_FILE):
        with open(HEALTH_FILE, "r") as f:
            return json.load(f)
    return []

def save_health(health):
    with open(HEALTH_FILE, "w") as f:
        json.dump(health, f, indent=2)

# ── MEDICINES ──────────────────────────────────────────────────────────────────

@app.route("/medicines", methods=["GET"])
def get_medicines():
    return jsonify(load_medicines())

@app.route("/medicines", methods=["POST"])
def add_medicine():
    data = request.json
    required = ["name", "dosage", "time", "frequency", "notes"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    medicines = load_medicines()
    new_med = {
        "id": int(datetime.datetime.now().timestamp() * 1000),
        "name": data["name"],
        "dosage": data["dosage"],
        "time": data["time"],          # "HH:MM"
        "frequency": data["frequency"], # daily / weekly / as-needed
        "notes": data.get("notes", ""),
        "color": data.get("color", "#6C63FF"),
        "taken_today": False,
        "last_taken": None,
        "snoozed_until": None,
        "stopped": False,
        "created_at": datetime.datetime.now().isoformat()
    }
    medicines.append(new_med)
    save_medicines(medicines)
    return jsonify(new_med), 201

@app.route("/medicines/<int:med_id>", methods=["DELETE"])
def delete_medicine(med_id):
    medicines = load_medicines()
    medicines = [m for m in medicines if m["id"] != med_id]
    save_medicines(medicines)
    return jsonify({"success": True})

@app.route("/medicines/<int:med_id>/taken", methods=["POST"])
def mark_taken(med_id):
    medicines = load_medicines()
    now = datetime.datetime.now().isoformat()
    for m in medicines:
        if m["id"] == med_id:
            m["taken_today"] = True
            m["last_taken"] = now
            m["stopped"] = True
            m["snoozed_until"] = None
            break
    save_medicines(medicines)
    return jsonify({"success": True})

@app.route("/medicines/<int:med_id>/snooze", methods=["POST"])
def snooze_medicine(med_id):
    medicines = load_medicines()
    minutes = request.json.get("minutes", 5)
    snooze_until = (datetime.datetime.now() + datetime.timedelta(minutes=minutes)).isoformat()
    for m in medicines:
        if m["id"] == med_id:
            m["snoozed_until"] = snooze_until
            m["stopped"] = False
            break
    save_medicines(medicines)
    return jsonify({"success": True, "snooze_until": snooze_until})

@app.route("/medicines/<int:med_id>/stop", methods=["POST"])
def stop_reminder(med_id):
    medicines = load_medicines()
    for m in medicines:
        if m["id"] == med_id:
            m["stopped"] = True
            m["snoozed_until"] = None
            break
    save_medicines(medicines)
    return jsonify({"success": True})

@app.route("/medicines/reset-daily", methods=["POST"])
def reset_daily():
    """Reset taken_today and stopped flags (call at midnight or manually)"""
    medicines = load_medicines()
    for m in medicines:
        m["taken_today"] = False
        m["stopped"] = False
        m["snoozed_until"] = None
    save_medicines(medicines)
    return jsonify({"success": True})

# ── REMINDERS ─────────────────────────────────────────────────────────────────

@app.route("/reminders/due", methods=["GET"])
def get_due_reminders():
    """Return medicines whose reminder should currently fire."""
    medicines = load_medicines()
    now = datetime.datetime.now()
    due = []

    for m in medicines:
        if m.get("taken_today") or m.get("stopped"):
            continue

        # Check snooze
        if m.get("snoozed_until"):
            snooze_dt = datetime.datetime.fromisoformat(m["snoozed_until"])
            if now < snooze_dt:
                continue  # still snoozed

        # Parse scheduled time (use today's date)
        try:
            scheduled = datetime.datetime.strptime(
                now.strftime("%Y-%m-%d") + " " + m["time"], "%Y-%m-%d %H:%M"
            )
        except ValueError:
            continue

        diff = abs((now - scheduled).total_seconds())
        # Fire within ±2 minutes of scheduled time, or if snooze has expired
        if diff <= 120 or (m.get("snoozed_until") and now >= datetime.datetime.fromisoformat(m["snoozed_until"])):
            due.append(m)

    return jsonify(due)

# ── HEALTH ────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def get_health():
    return jsonify(load_health())

@app.route("/health", methods=["POST"])
def add_health():
    data = request.json
    health = load_health()
    entry = {
        "id": int(datetime.datetime.now().timestamp() * 1000),
        "date": datetime.date.today().isoformat(),
        "time": datetime.datetime.now().strftime("%H:%M"),
        "bp_systolic": data.get("bp_systolic", ""),
        "bp_diastolic": data.get("bp_diastolic", ""),
        "sugar": data.get("sugar", ""),
        "weight": data.get("weight", ""),
        "notes": data.get("notes", "")
    }
    health.append(entry)
    save_health(health)
    return jsonify(entry), 201

@app.route("/health/<int:entry_id>", methods=["DELETE"])
def delete_health(entry_id):
    health = load_health()
    health = [h for h in health if h["id"] != entry_id]
    save_health(health)
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True, port=5000)