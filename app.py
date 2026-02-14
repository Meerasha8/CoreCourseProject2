from flask import Flask, request, jsonify, render_template, send_from_directory
import sqlite3
from datetime import datetime
import os
import cv2
import numpy as np
from ultralytics import YOLO

app = Flask(__name__)

# ---------------- YOLO MODEL LOAD ----------------

# Put your trained model in project root

model = YOLO("yolov8n_insect.pt")

# ---------------- IMAGE STORAGE ----------------

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DB INIT ----------------

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            temperature REAL,
            humidity REAL,
            time TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spray INTEGER DEFAULT 0,
            light INTEGER DEFAULT 0,
            buzzer INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS pest_alert (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            detected INTEGER,
            time TEXT
        )
    """)

    c.execute("SELECT COUNT(*) FROM commands")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO commands VALUES (1,0,0,0,?)",
                (datetime.now().isoformat(),))

    conn.commit()
    conn.close()

init_db()

# ---------------- FRONTEND ----------------

@app.route("/")
def index():
    return render_template("index.html")

# ---------------- SENSOR DATA ----------------

@app.route("/api/sensor", methods=["POST"])
def receive_sensor():
    data = request.json
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute(
        "INSERT INTO sensor_data VALUES (NULL,?,?,?)",
        (data["temperature"], data["humidity"], data["time"])
    )

    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


# ---------------- GET COMMAND ----------------

@app.route("/api/command")
def get_command():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT spray, light, buzzer FROM commands WHERE id=1")
    row = c.fetchone()
    conn.close()

    return jsonify({
        "spray": row[0],
        "light": row[1],
        "buzzer": row[2]
    })

# ---------------- CONTROL ----------------

@app.route("/api/control", methods=["POST"])
def control():
    data = request.json
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        UPDATE commands
        SET spray=?, light=?, buzzer=?, updated_at=?
        WHERE id=1
    """, (
        data.get("spray", 0),
        data.get("light", 0),
        data.get("buzzer", 0),
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()
    return jsonify({"status": "updated"})

# ---------------- IMAGE UPLOAD + YOLO ----------------

@app.route("/upload", methods=["POST"])
def upload_image():
    if not request.data:
        return jsonify({"error": "no_image"}), 400

    # Save image
    filename = datetime.now().strftime("%Y%m%d%H%M%S") + ".jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    with open(filepath, "wb") as f:
        f.write(request.data)

    # ---------- YOLO DETECTION ----------
    img = cv2.imread(filepath)
    results = model(img)

    pest_detected = 0

    for r in results:
        if len(r.boxes) > 0:
            pest_detected = 1

    # ---------- SAVE ALERT ----------
    if pest_detected == 1:
        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute(
            "INSERT INTO pest_alert VALUES (NULL,?,?)",
            (1, datetime.now().isoformat())
        )

        c.execute("UPDATE commands SET buzzer=1 WHERE id=1")

        conn.commit()
        conn.close()

    return jsonify({
        "status": "processed",
        "pest_detected": pest_detected
    })

# ---------------- SERVE IMAGES ----------------

@app.route("/uploads/<filename>")
def get_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ---------------- LATEST PEST ----------------

@app.route("/api/pest/latest")
def latest_pest():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
    SELECT detected, time
    FROM pest_alert
    ORDER BY id DESC LIMIT 1
    """)
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({"detected": row[0], "time": row[1]})
    return jsonify({"detected": 0})

if __name__ == "__main__":
    app.run(debug=True)
