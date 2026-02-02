from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime

app = Flask(__name__)

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

    # Ensure one command row exists
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

# ---------------- ESP32: SENSOR DATA ----------------
@app.route("/api/sensor", methods=["POST"])
def receive_sensor():
    data = request.json
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute(
        "INSERT INTO sensor_data (temperature, humidity, time) VALUES (?,?,?)",
        (data["temperature"], data["humidity"], data["time"])
    )

    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# ---------------- ESP32: GET COMMAND ----------------
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

# ---------------- FRONTEND BUTTONS ----------------
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

# ---------------- YOLO PEST ALERT ----------------
@app.route("/api/pest", methods=["POST"])
def pest_alert():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute(
        "INSERT INTO pest_alert (detected, time) VALUES (?,?)",
        (1, datetime.now().isoformat())
    )

    # Activate buzzer automatically
    c.execute("UPDATE commands SET buzzer=1 WHERE id=1")

    conn.commit()
    conn.close()
    return jsonify({"status": "pest_detected"})

# ---------------- FETCH DATA FOR UI ----------------
@app.route("/api/data")
def get_data():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        SELECT temperature, humidity, time
        FROM sensor_data
        ORDER BY id DESC LIMIT 20
    """)
    rows = c.fetchall()
    conn.close()

    return jsonify(rows)

@app.route("/api/pest/latest")
def latest_pest():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        SELECT detected, time
        FROM pest_alert
        ORDER BY id DESC
        LIMIT 1
    """)
    row = c.fetchone()
    conn.close()

    if row:
        return jsonify({"detected": row[0], "time": row[1]})
    return jsonify({"detected": 0})

@app.route("/api/latest")
def latest_sensor():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        SELECT temperature, humidity, time
        FROM sensor_data
        ORDER BY id DESC
        LIMIT 1
    """)
    row = c.fetchone()
    conn.close()

    if row:
        return jsonify({
            "temperature": row[0],
            "humidity": row[1],
            "time": row[2]
        })
    return jsonify({})



if __name__ == "__main__":
    app.run(debug=True)
